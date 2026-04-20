# fw options
Given that there's two cpus in paralell, there's... multiple options for firmware.  First off, we're having micropython on the esp32, as a baseline.

We'll probably also try esphome on the esp32.

For the ch584, ... could be anything yet ;)


# micropython builds esp32-c3

We prefer using idf in a container.
but make submodules doens't work well like that?
like  podman run --rm  -v .:/project:Z -w /project/lib/micropython/ports/esp32 -e HOME=/tmp docker.io/espressif/idf:v5.5.1 make submodules
 should be ok, nbut... it isn't just do the submodules by hand and move on with life...

```
git submodule update --init lib/berkeley-db-1.xx lib/micropython-lib
```

```
podman run --rm  -v .:/project:Z -w /project/boards/ktwinkler-multi-r2025-12 -e HOME=/tmp docker.io/espressif/idf:v5.5.1 idf.py  build
```
# To flash.
```
podman run --rm --device /dev/ttyACM0 -v .:/project:Z -w /project/boards/ktwinkler-multi-r2025-12 -e HOME=/tmp docker.io/espressif/idf:v5.5.1 idf.py -b 921660 build erase-flash flash
```
