#!python3
"""
This is ... a method. It's fine for a couple of static devices,
not sure I really like it long term though, I think mqtt or btle provisioning
would be better long term
"""

import machine
import binascii

# Dataclasses are ideal, but not in mpy. (but mpy has named tuples? maybe another day...)
class NodeConfig:
    def __init__(self, device_uid, **kwargs):
        self.device_uid = device_uid
        self.artnet_channel = kwargs.get("artnet_channel", 42)
        # At least at this stage, we're defaulting to a single twinkler per node.
        # We'll need further thought later...
        self.artnet_length = kwargs.get("artnet_length", 2)
        self.artnet_universe = kwargs.get("artnet_universe", 0)


static_data = {
    # The purple reworked ktwinklermulti with the cut tracks
    b"70af091689f8" : NodeConfig("70af091689f8", artnet_channel=2),
    # TTGO display
    b'246f28250538' : NodeConfig("246f28250538", artnet_channel=3),
}

def lookup_config():
    key = binascii.hexlify(machine.unique_id())
    cfg = static_data.get(key, None)
    if cfg is None:
        raise ValueError("No configuration found for device UID: {}".format(key))
    return cfg
