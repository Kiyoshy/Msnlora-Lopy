# boot.py -- run on boot-up
import machine
from network import WLAN
wlan = WLAN(mode=WLAN.STA)
wlan.deinit()
