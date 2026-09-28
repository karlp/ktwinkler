#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdint.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <sys/queue.h>
#include <unistd.h>

#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "nvs_flash.h"
#include "sdkconfig.h"
#include "lwip/inet.h"
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"
#include "freertos/semphr.h"
#include "freertos/task.h"


#define RX_BUFFER_SIZE  1500
#define TIMING_HISTORY_SIZE 50

typedef struct timing_sample {
	TAILQ_ENTRY(timing_sample) entries;
	int64_t t_delta_us;
} timing_sample_t;

TAILQ_HEAD(timing_history, timing_sample);
static struct timing_history s_timing_history;
static timing_sample_t s_timing_samples[TIMING_HISTORY_SIZE];
static size_t s_timing_sample_count;
static SemaphoreHandle_t s_timing_mutex;

static const char *TAG = "udp_rx";
static EventGroupHandle_t s_wifi_event_group;
static const EventBits_t WIFI_CONNECTED_BIT = BIT0;

static void wifi_event_handler(void *arg, esp_event_base_t event_base,
							   int32_t event_id, void *event_data)
{
	(void)arg;
	(void)event_data;

	if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
		ESP_ERROR_CHECK(esp_wifi_connect());
	} else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
		xEventGroupClearBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
		ESP_LOGW(TAG, "Wi-Fi disconnected; reconnecting");
		esp_wifi_connect();
	} else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
		xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
	}
}

static void wifi_init_sta(void)
{
	s_wifi_event_group = xEventGroupCreate();
	ESP_ERROR_CHECK(esp_netif_init());
	ESP_ERROR_CHECK(esp_event_loop_create_default());
	esp_netif_create_default_wifi_sta();

	wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
	ESP_ERROR_CHECK(esp_wifi_init(&cfg));
	ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID,
											   wifi_event_handler, NULL));
	ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP,
											   wifi_event_handler, NULL));

	wifi_config_t wifi_config = {
		.sta = {
			.ssid = CONFIG_UDP_RX_WIFI_SSID,
			.password = CONFIG_UDP_RX_WIFI_PASSWORD,
			.threshold.authmode = WIFI_AUTH_WPA2_PSK,
		},
	};
	ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
	ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
	ESP_ERROR_CHECK(esp_wifi_start());

	ESP_LOGI(TAG, "Connecting to Wi-Fi...");
	xEventGroupWaitBits(s_wifi_event_group, WIFI_CONNECTED_BIT, pdFALSE,
						pdTRUE, portMAX_DELAY);
	ESP_LOGI(TAG, "Wi-Fi connected");
}

static void task_tick(void *arg)
{
	(void)arg;
	int i = 0;
	while (true) {
		int64_t min_us = INT64_MAX;
		int64_t max_us = 0;
		int64_t total_us = 0;
		size_t count = 0;

		xSemaphoreTake(s_timing_mutex, portMAX_DELAY);
		timing_sample_t *sample;
		TAILQ_FOREACH(sample, &s_timing_history, entries) {
			if (sample->t_delta_us < min_us) min_us = sample->t_delta_us;
			if (sample->t_delta_us > max_us) max_us = sample->t_delta_us;
			total_us += sample->t_delta_us;
			count++;
		}
		xSemaphoreGive(s_timing_mutex);

		if (count > 0) {
			ESP_LOGI(TAG, "tick %d: recv() timing over %u samples (us): min=%lld avg=%lld max=%lld",
					 i++, (unsigned)count, (long long)min_us,
					 (long long)(total_us / count), (long long)max_us);
		} else {
			ESP_LOGI(TAG, "tick %d: no UDP receive samples yet", i++);
		}
		vTaskDelay(pdMS_TO_TICKS(1000));
	}
}

static void record_t_delta(int64_t t_delta_us)
{
	xSemaphoreTake(s_timing_mutex, portMAX_DELAY);

	timing_sample_t *sample;
	if (s_timing_sample_count < TIMING_HISTORY_SIZE) {
		sample = &s_timing_samples[s_timing_sample_count++];
	} else {
		// Reuse the oldest node to keep only the 50 most recent measurements.
		sample = TAILQ_FIRST(&s_timing_history);
		TAILQ_REMOVE(&s_timing_history, sample, entries);
	}
	sample->t_delta_us = t_delta_us;
	TAILQ_INSERT_TAIL(&s_timing_history, sample, entries);

	xSemaphoreGive(s_timing_mutex);
}

static void udp_receiver_task(void *arg)
{
	(void)arg;

	int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_IP);
	if (sock < 0) {
		ESP_LOGE(TAG, "socket() failed: errno %d", errno);
		vTaskDelete(NULL);
		return;
	}

	int flags = fcntl(sock, F_GETFL, 0);
	if (flags < 0 || fcntl(sock, F_SETFL, flags | O_NONBLOCK) < 0) {
		ESP_LOGE(TAG, "could not set socket non-blocking: errno %d", errno);
		close(sock);
		vTaskDelete(NULL);
		return;
	}

	const struct sockaddr_in bind_addr = {
		.sin_family = AF_INET,
		.sin_port = htons(CONFIG_UDP_RX_PORT),
		.sin_addr.s_addr = htonl(INADDR_ANY),
	};
	if (bind(sock, (const struct sockaddr *)&bind_addr, sizeof(bind_addr)) < 0) {
		ESP_LOGE(TAG, "bind() on UDP port %d failed: errno %d", CONFIG_UDP_RX_PORT, errno);
		close(sock);
		vTaskDelete(NULL);
		return;
	}

	ESP_LOGI(TAG, "Listening for UDP datagrams on port %d", CONFIG_UDP_RX_PORT);
	uint8_t buffer[RX_BUFFER_SIZE];
	while (true) {
		//struct sockaddr_in source_addr;
		//socklen_t source_addr_len = sizeof(source_addr);
		// ssize_t len = recvfrom(sock, buffer, sizeof(buffer), 0,
		// 					   (struct sockaddr *)&source_addr, &source_addr_len);
		int64_t t1 = esp_timer_get_time();
		ssize_t len = recv(sock, buffer, sizeof(buffer), 0);
		int64_t t_delta = esp_timer_get_time() - t1;

		if (len >= 0) {
			// ESP_LOGI(TAG, "Received %d bytes from %s:%u", (int)len,
			// 		 inet_ntoa(source_addr.sin_addr), ntohs(source_addr.sin_port));
			ESP_LOGI(TAG, "Received %d bytes", (int)len);
			record_t_delta(t_delta);
		} else if (errno != EAGAIN && errno != EWOULDBLOCK) {
			ESP_LOGW(TAG, "recvfrom() failed: errno %d", errno);
		}

		// recvfrom() returns immediately when there is no packet; yield instead of busy-spinning.
		vTaskDelay(pdMS_TO_TICKS(10));
	}
}

void app_main(void)
{
	TAILQ_INIT(&s_timing_history);
	s_timing_mutex = xSemaphoreCreateMutex();
	ESP_ERROR_CHECK(s_timing_mutex != NULL ? ESP_OK : ESP_ERR_NO_MEM);

	esp_err_t ret = nvs_flash_init();
	if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
		ESP_ERROR_CHECK(nvs_flash_erase());
		ret = nvs_flash_init();
	}
	ESP_ERROR_CHECK(ret);
	wifi_init_sta();
	xTaskCreate(udp_receiver_task, "udp_receiver", 4096, NULL, 5, NULL);
	xTaskCreate(task_tick, "tick", 4096, NULL, 5, NULL);
}