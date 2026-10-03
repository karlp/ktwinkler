# twinkler 24V garden
24v "field" bus lying around the garden, for smallish wires and enough power.
5V "led" bus light for the light strings I know I have
3.3v for an esp32
2x antiparallel led channels. (maybe a third if I can juggle the pins)
ufl antenna mount by default, but onboard PIFA as well.
designed to fit into some cheapish aliexpress waterproof junction boxes


# Bugs
This version won't boot with only the USB supply, it sags too much on startup.
This is because I didn't put enough decoupling on the esp32-c3.  Adding 10uF at
pin2 and 10uF at pin 31 fixed it, and is more inline with the hardware design guidelines
I believe earlier hardware had been sharing input caps with other portions of the boards,
so it wasn't noticed.

# Enhancements for a future version
* Remember rememeber, always add a nice place for a ground clip.
* you put a 3A supply down, it might have been nice to provide an output for that supply, instead
  of just burying it and only using it to power the drivers.
