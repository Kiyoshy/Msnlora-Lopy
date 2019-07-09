# Messenger LoRa

Low-power system to connect isolated communities based on the LoRa protocol to provide a messaging system to registered users using LoPy devices.

Based on https://github.com/gie-sakura/msnlora

### Technical details

   - Device: Pycom LoPy4
   - Firmware version: 1.18.2.r3

### Current limitations
This version is capable of transmitting 100KB.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes in your lopy. 

### Prerequisites

In the lopy device:

This is the basic information required to set up a suitable development environment for a Pycom device, in this case the LoPys.

You first need to have Python 3 and Pip 3 installed in your computer. Check here for the proper instructions and code:
```
https://www.python.org/download/releases/3.0/

$ sudo apt install python3
$ sudo apt install python3-pip
```

Install the software required to connect to the LoPy device
```
$ sudo python3 -m pip install mpy-repl-tool
```

For more information you can check the full [documentation](https://docs.pycom.io/)

### Installing

Now you can download and install the project in your devices.

First download the .ZIP, extract it in your machine.

To install the repository in the LoPy device, open a terminal on the project's location.

Verify if the device has been recognized:
```
$ sudo python3 -m there detect
```

Confirm that the device only contains the main.py and boot.py files:
```
$ sudo python3 -m there ls -l /flash/ *
```

If the device contains more files, it must be formatted type (otherwise, go to the next step):
```
$ sudo python3 -m there -i
	>>> import os
    >>> os.mkfs ("/flash")
    >>> Crtl + AltGr + ]
```

Upload the files of the repository to the device:
```
$ sudo python3 -m there push * /flash
```

Get access to the REPL prompt:
```
$ sudo python3 -m there -i
```

## Deployment

Once in the REPL promt import the server file and choose the execution mode
```
import server
```
Connect to the network and type the address
```
192.168.4.1
```

## Authors

* **Miguel Kiyoshy Nakamura Pinto**
* **Angélica Moreno Cárdenas**
* **Pietro Manzoni**

## License

This project is licensed under the GNU GPLv3 - see the [LICENSE.md](license.md) file for details

## Acknowledgments

* **Ermanno Pietrosemoli**
* **Marco Zennaro**
* **Marco Rainone**