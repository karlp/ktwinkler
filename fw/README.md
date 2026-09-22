# fw options
Given that there's multiple boards, with multiple hardwares in this repo, the firmware really has a few options.  At the time of writing, work is focused on esp32 variants, and using them with home assistant, and/or Artnet or sACN/E1.31


# micropython builds

## One time prep
We prefer using idf in a container, however, the original "make submodules" targets inside esp32 aren't happy with that.  Just update the submodules we know ahead of time.
```
git submodule update --init lib/micropython-lib lib/berkeley-db-1.xx
```

## (re)build
```
podman run --rm  -v .:/project:Z -w /project/boards/ktwinkler-multi-r2025-12 -e HOME=/tmp docker.io/espressif/idf:v5.5.4 idf.py  build
```

# To flash.
```
podman run --rm --device /dev/ttyACM0 -v .:/project:Z -w /project/boards/ktwinkler-multi-r2025-12 -e HOME=/tmp docker.io/espressif/idf:v5.5.1 idf.py -b 921660 build erase-flash flash
```
