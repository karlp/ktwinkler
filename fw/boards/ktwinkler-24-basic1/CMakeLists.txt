cmake_minimum_required(VERSION 3.16)

get_filename_component(PROJECT_DIR "../.." ABSOLUTE)
set(MICROPY_PORT_DIR ${PROJECT_DIR}/lib/micropython/ports/esp32)
get_filename_component(MICROPY_BOARD_DIR "." ABSOLUTE)

# If unset, will default to directory name of the board.
#set(MICROPY_HW_BOARD_NAME "ESP32_MOS_X4")
# If unset, will default to IDF target
#set(MICROPY_HW_MCU_NAME "ESP32lol")

include(../mpy.esp32.common2.cmake)

# Define the project.
project(micropython)