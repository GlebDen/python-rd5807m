# -*- coding: utf8 -*-

import ast
import asyncio
import sys
import time

from rda5807m import Rda5807m


class Radio:

    def __init__(self):
        self.radio = Rda5807m(1)

        self.commands = {
            "off": {"call": self.radio.off},
            "bass": {"call": self.radio.set_bass, "type": bool},
            "mute": {"call": self.radio.set_mute, "value": True},
            "unmute": {"call": self.radio.set_mute, "value": False},
            "stereo": {"call": self.radio.set_stereo, "value": True},
            "mono": {"call": self.radio.set_stereo, "value": False},
            "volume": {"call": self.set_volume, "type": int},
            "frequency": {"call": self.set_frequency, "type": float},
            "de-emphasis": {"call": self.set_deemphasis, "type": int},
        }

    def initialize(self):
        try:
            state = self.radio.init_chip()
        except:
            print("problem while initializing")
            loop.stop()
        if not state:
            self.radio.write_setting()
            time.sleep(0.2)

    def print_prompt(self):
        print(">> ", end="", flush=True)

    def got_stdin_data(self):
        input_string = sys.stdin.readline().strip('\n')
        if input_string != "":
            self.parse_command(input_string)
        self.print_prompt()

    def parse_command(self, entry):
        if entry == "quit":
            loop.stop()
        elif entry == "help":
            print("commands :")
            print("   off")
            print("   help")
            print("   bass=<bool>")
            print("   mute")
            print("   unmute")
            print("   mono")
            print("   stereo")
            print("   volume=<int>")
            print("   frequency=<float>")
            print("   de-emphasis=<int>")
        else:
            parts = entry.split('=')
            command = parts[0]
            if command in self.commands:
                params = self.commands[command]
                call = params["call"]
                if len(parts) == 1:
                    if "value" in params:
                        value = params["value"]
                        call(value)
                    else:
                        call()
                elif len(parts) == 2:
                    value = ast.literal_eval(parts[1])
                    if "type" in params:
                        type_ = params["type"]
                        if type(value) == type_:
                            call(value)
                        else:
                            print("bad value type")
                    else:
                        print("invalid syntax")
                else:
                    print("invalid syntax")
            else:
                print("command not found")

    def set_volume(self, volume):
        if not 0 <= volume <= 15:
            print("bad volume value (0-15)")
            return
        self.radio.set_volume(volume)

    def set_frequency(self, frequency):
        if not 76 <= frequency <= 107.5:
            print("bad frequency value (76-107.5)")
        frequency = int(frequency * 10)
        self.radio.set_frequency(frequency)

    def set_deemphasis(self, deemphasis):
        if deemphasis not in [50, 75]:
            print("bad de-emphasis value (50, 75)")
        self.radio.set_deemphasis(deemphasis)

    def close(self):
        self.radio.close()


radio = Radio()
radio.initialize()
radio.parse_command("help")
radio.print_prompt()

loop = asyncio.get_event_loop()
loop.add_reader(sys.stdin, radio.got_stdin_data)
loop.run_forever()

radio.close()
