#!python3
"""
Phase style twinkler.
This is currently in a separate file, but maybe eventually this all gets merged in as just different pieces...

This _requires_ a machine.PWM implementatation that supports phase control.
An example is contained in: https://github.com/karlp/micropython/commit/b9ac3268f56ecccd15d85813a255109e2bea64ce
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

class TwinklPhased:
    def __init__(self, p1=def_p1, p2=def_p2, f=5000):
        self.w = [machine.PWM(p1, freq=f, duty=0), machine.PWM(p2, freq=f, duty=0)]
        if "hpoint" not in dir(self.w[0]):
            raise AttributeError("You need the 'hpoint' patch for esp32-pwm to use this module")
        self._logical = [0, 0]

    # FIXME - do I want to have a 0..100% here?!
    # Or just keep it at 0..1023 like esp32 limits?
    def set_logical(self, logical):
        self._logical = logical

        if all(self._logical):
            """
            Bi-colour, must split the space to allow maximul
            We're splitting the phase into 2 portions, one for each colour.
            Yes, that means that 100% brightness with two colours is only 50% brightness?
            You can _absolutely_ go bananas here on how to share the brightness, but what we
            really want is ~mostly what would be sort of expected, and nothing crazy.
            set 1 to 100%, get 100%
            set 2 to 100% get... "max" brightness for both, though they're both now dim seems _reasonable_ to me.
            setting 2 back to 0 will _increase_ 1's power, not just relative, it will double!
            
            Any sort of _fading_ up and through though?....
            I mean, another option is to permanently reserve 50% power for whether the other direction gets used,
            and that seems... arguably less useful?
            Anyway, we're goign to start with just dividing the space in half, _when needed_ and scale the duty.
            so going from "1023" duty on both channels to 1023 duty on one cahnnel will instantly brighten that one, 
            more than just "turn off" the other... that will ... do fo

            Where it kinda falls down is where you dim down one channel, when it finally hits zero, the other one gets _noticeably_ brighter?
            """
            # we can set them both to the same duty, 50%, and vary hpoint from 0..2048 and 2048..4096?
            self.w[1].hpoint(4096)
            self.w[0].duty(self._logical[0] // 2)
            self.w[1].duty(self._logical[1] // 2)

        elif any(self._logical):
            """
            Only one channel in use, just accept it as is, full range of power.
            """
            if (self._logical[0]):
                self.w[0].duty(self._logical[0])
                self.w[1].duty(0)
            else:
                self.w[0].duty(0)
                self.w[1].duty(self._logical[1])
        else:
            # both off then..
            [px.duty(0) for px in self.w]



    def get_logical(self):
        return self._logical




if __name__ == "__main__":
    tt = TwinklPhased()