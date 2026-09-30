#!python3
"""
asyncio twinkler.
antiparallel led drivers (h-bridge style)

This provides building blocks for plugging into an asyncio system

Remember: any "simulataneous" dual colour needs to run a fast alternating loop! (somewhere!)
"""

import asyncio
import machine
import time

def_p1 = None
def_p2 = None
if "PWM1" in dir(machine.Pin.board):
    def_p1 = machine.Pin.board.PWM1
if "PWM2" in dir(machine.Pin.board):
    def_p2 = machine.Pin.board.PWM2

class TwinklAsync:
    def __init__(self, p1=def_p1, p2=def_p2, f=5000, async_step_ms=20):
        self.w = [machine.PWM(p1, freq=f, duty=0), machine.PWM(p2, freq=f, duty=0)]
        self._logical = [0, 0]
        self.async_step_ms = async_step_ms
        self.ev_update = asyncio.Event()

    # FIXME - do I want to have a 0..100% here?!
    def set_logical(self, logical):
        self._logical = logical
        self.ev_update.set()

    def set_logical_single(self, sel, value):
        self._logical[sel] = value
        self.ev_update.set()

    def get_logical(self):
        return self._logical

    async def task_maintain_logical(self):
        """
        You must run this task in the asyncio event loop to maintain the logical LED states correctly.
        """
        while True:
            await self.ev_update.wait()
            self.ev_update.clear()
            if all(self._logical):
                # Both on, must alternate between them
                self.ev_update.set()
                self.w[0].duty(self._logical[0])
                self.w[1].duty(0)
                await asyncio.sleep_ms(self.async_step_ms)
                self.w[0].duty(0)
                self.w[1].duty(self._logical[1])
                await asyncio.sleep_ms(self.async_step_ms)
                # Just one pass then recheck things...
                continue
            elif any(self._logical):
                # Just set the one that is on, and the other off...
                # (avoids flicker when we don't need it)
                if self._logical[0]:
                    self.w[0].duty(self._logical[0])
                    self.w[1].duty(0)
                else:
                    self.w[0].duty(0)
                    self.w[1].duty(self._logical[1])
                await asyncio.sleep_ms(self.async_step_ms)
                continue
            else:
                self.w[0].duty(0)
                self.w[1].duty(0)
                await asyncio.sleep_ms(self.async_step_ms)
                continue


    # Just let people access self.logical[] directly?
    # def single(self, sel, brightness):
    #     other = 0
    #     if sel == 0:
    #         other = 1
    #     self.logical[sel] = brightness
    #     self.logical[other] = 0

    # Blink a single LED asynchronously
    async def t_blink_single(self, sel, brightness, step_time_ms=100):
        other = 0
        if sel == 0:
            other = 1
        self.set_logical_single(other, 0)
        while True:
            self.set_logical_single(sel, brightness)
            await asyncio.sleep_ms(step_time_ms)
            self.set_logical_single(sel, 0)
            await asyncio.sleep_ms(step_time_ms)

    async def t_fade_single(self, sel, start_brightness, end_brightness, duration_ms=2000):
        other = 0
        if sel == 0:
            other = 1
        self.set_logical_single(other, 0)
        # TODO - adjust/provide a parameter to control the speed better?
        # we want a time to cover the entire fade from start to end
        # with a reasonable number of steps between?
        delta = end_brightness - start_brightness
        # divide duration by delta to get the step time => 100 steps over 2000 = 10 ms per step
        if delta > 0:
            b_step = 1
        else:
            b_step = -1
    
        step_time_ms = abs(duration_ms / delta)
        # 50 brightness over 5000 => 100ms steps, 1brightness per step
        # 50 brightness over 100 => 2ms per step, 1 brightness per step
        # 50 brightness over 20 => 0.4ms per step, too fine, instead do 1ms per step, with 50/20 per step...

        if step_time_ms >= 1:
            # Good path, do _1_ brightness per step
            step_time_ms = int(step_time_ms)
        else:
            step_time_ms = 1
            # fixme - recalc bstep based on how much we need
            b_step = int(delta / duration_ms)

        for brightness in range(start_brightness, end_brightness + b_step, b_step):
            self.set_logical_single(sel, brightness)
            await asyncio.sleep_ms(step_time_ms)


def atest1(tt: TwinklAsync):
    """
    Simple test function to blink the first LED of the TwinklAsync instance.
    """

    async def test_task():
        i = 1
        while i > 0:
            await asyncio.sleep_ms(40)
            # Yes, this will betray asyncio
            #time.sleep_ms(5)
            i += 1
            #print(f"async Loop iteration {i}")

    async def test_time_requirements():
        """
        Test how much interruption the asyncio maintenance loop tolerates
        when using dual dimmed leds (ie, needing to constantly reverse pwm)
        """
        b = 0
        step = 100
        
        while True:
            #print(f"setting both to {b}")
            tt.set_logical([b, b])
            b += step
            if b > 1023:
                b = 1023
                step = -step
            if b < 0:
                b = 0
                step = -step
            await asyncio.sleep_ms(1000)

    async def k_show_1():
        tt.set_logical([0, 255])
        await asyncio.sleep_ms(400)
        tt.set_logical([255, 0])
        await asyncio.sleep_ms(400)

        await tt.t_fade_single(0, 0, 100, 2000)

        steps = [800, 800, 800, 800, 400, 400, 400, 400, 200, 200, 200, 200]
        for i, t in enumerate(steps):
            a = [800, 0]
            b = [0, 800]
            sel = i % 2
            if sel:
                tt.set_logical(b)
            else:
                tt.set_logical(a)
            await asyncio.sleep_ms(t)


        while True:
            await asyncio.sleep_ms(400)
            print("finished test routing...")

    async def main_task():
        asyncio.create_task(tt.task_maintain_logical())
        #asyncio.create_task(tt.blink_single(0, 100))
        #asyncio.create_task(tt.t_blink_single(0, 100))
        #asyncio.create_task(tt.t_fade_single(0, 0, 100, 2000))
        asyncio.create_task(test_task())
        #asyncio.create_task(k_show_1())
        asyncio.create_task(test_time_requirements())

        while True:
            await asyncio.sleep_ms(2000)
            print("Main loop iteration hoho")

    try:
        asyncio.run(main_task())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    tt = TwinklAsync()
    atest1(tt)