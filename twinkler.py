#!python3
"""
Exploring antiparallel led driving
"""

import machine
import time

class Twinkl:
    def __init__(self, p1=machine.Pin.board.PWM2, p2=machine.Pin.board.PWM3, f=5000):
        self.w = [machine.PWM(p1, freq=f, duty=0), machine.PWM(p2, freq=f, duty=0)]

    def single(self, sel, brightness):
        other = 0
        if sel == 0:
            other = 1
        self.w[other].duty(0)
        self.w[sel].duty(brightness)

    def blink_single(self, sel, brightness, step_time_ms=100):
        other = 0
        if sel == 0:
            other = 1
        self.w[other].duty(0)
        while True:
            self.w[sel].duty(brightness)
            time.sleep_ms(step_time_ms)
            self.w[sel].duty(0)
            time.sleep_ms(step_time_ms)

    def fade_single(self, sel, bmin, bmax, freq=2):
        # This feels a little clunky, what other apis could we do for this...
        other = 0
        if sel == 0:
            other = 1
        self.w[other].duty(0)
        cycle_ms = 1000/freq
        # TODO iterate to find a reasonabl step time?
        step_time_ms = 10
        steps = (int(cycle_ms) / step_time_ms) / 2
        delta = int((bmax - bmin) / steps)
        for i in range(steps):
            # sin? no, fuck that... but yes, you should...
            self.w[sel].duty(i*delta + bmin)
            time.sleep_ms(step_time_ms)
        for i in range(steps):
            self.w[sel].duty(bmax - i*delta)
            time.sleep_ms(step_time_ms)

    def fade_both(self, bmin, bmax, freq=2):
        cycle_ms = 1000/freq
        # TODO iterate to find a reasonabl step time?
        step_time_ms = 10
        steps = (int(cycle_ms) / step_time_ms) * 2
        delta = int((bmax - bmin) / steps)
        for i in range(steps):
            # evenly share this slot for both directions
            b = i*delta + bmin
            for k in range(step_time_ms):
                sel = k % 2
                other = (k+1)%2
                self.w[sel].duty(b)
                self.w[other].duty(0)
                time.sleep_ms(1)
        for i in range(steps):
            b = bmax - i*delta
            for k in range(step_time_ms):
                sel = k % 2
                other = (k+1)%2
                self.w[sel].duty(b)
                self.w[other].duty(0)
                time.sleep_ms(1)

    def twinkle(self, sel, nomb=900, freq=3, count=3, step_time_ms=30):
        " this is the sort of flicker a few times"
        other = 0
        if sel == 0:
            other = 1
        for i in range(count):
            self.fade_single(sel, 200, nomb, freq)
            time.sleep_ms(step_time_ms)


    def classic_alt(self, nomb=800):
        steps = [800, 800, 800, 800, 400, 400, 400, 400, 200, 200, 200, 200]
        for i, t in enumerate(steps):
            sel = i % 2
            other = (i+1)%2
            self.w[sel].duty(nomb)
            self.w[other].duty(0)
            time.sleep_ms(t)

    def classic_slow_fade(self, nomb=800, freq=1):
        while True:
            self.fade_single(0, 0, nomb, freq=freq/2)
            self.fade_single(1, 0, nomb, freq=freq/2)

    def classic_modes(self, mode):
        """
        1. combination
        2. in wave
        3. sequential
        4. slow glow
        5 chasing/flash
        6 slow fade
        7 twinkle/flash
        8 steady on
        9 off
        """
        pass