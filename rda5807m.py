# -*- coding: utf8 -*-

# RDA5807M Radio App for Raspberry Pi
# C version - redhawk 04/04/2014
# Python version version - Franck Barbenoire 17/03/2016
#
# This code is provided to help with programming the RDA chip.

from functools import partial
import pigpio
from string import printable

RDA_I2C_WRITE_ADDRESS = 0x10
RDA_I2C_READ_ADDRESS = 0x11

# CHIP ID
RDA_CHIP_ID = 0x58

# Timing XTAL
RDA_32_768KHZ = 0b0000000000000000
RDA_12MHZ = 0b0000000000010000
RDA_24MHZ = 0b0000000001010000
RDA_13MHZ = 0b0000000000100000
RDA_26MHZ = 0b0000000001100000
RDA_19_2MHZ = 0b0000000000110000
RDA_38_4MHZ = 0b0000000001110000

# Tuning Band
RDA_87_108MHZ = 0b0000000000000000
RDA_76_91MHZ = 0b0000000000000100
RDA_76_108MHZ = 0b0000000000001000
RDA_65_76MHZ = 0b0000000000001100

# Tuning Steps
RDA_100KHZ = 0b0000000000000000
RDA_200KHZ = 0b0000000000000001  # not US band compatible
RDA_50KHZ = 0b0000000000000010
RDA_25KHZ = 0b0000000000000011

# De-emphasis
RDA_50US = 0b0000100000000000
RDA_75US = 0b0000000000000000

# REG 0x02
RDA_DHIZ = 0b1000000000000000
RDA_DMUTE = 0b0100000000000000
RDA_MONO = 0b0010000000000000
RDA_BASS = 0b0001000000000000
RDA_RCLK = 0b0000100000000000
RDA_RCKL_DIM = 0b0000010000000000
RDA_SEEKUP = 0b0000001000000000
RDA_SEEK = 0b0000000100000000
RDA_SKMODE = 0b0000000010000000
RDA_CLK_MODE = 0b0000000001110000
RDA_RDS_EN = 0b0000000000001000
RDA_NEW_METHOD = 0b0000000000000100
RDA_SOFT_RESET = 0b0000000000000010
RDA_ENABLE = 0b0000000000000001

# REG 0x03
RDA_CHAN = 0b1111111111000000
RDA_DIRECT_MODE = 0b0000000000100000
RDA_TUNE = 0b0000000000010000
RDA_BAND = 0b0000000000001100
RDA_SPACE = 0b0000000000000011

# REG 0x04
RDA_DE = 0b0000100000000000
RDA_SOFTMUTE_EN = 0b0000001000000000
RDA_AFCD = 0b0000000100000000

# REG 0x05
RDA_INT_MODE = 0b1000000000000000
RDA_SEEKTH = 0b0000111100000000
RDA_VOLUME = 0b0000000000001111

# REG 0x06
RDA_OPEN_MODE = 0b0110000000000000

# REG 0x07
RDA_BLEND_TH = 0b0111110000000000
RDA_65_50M_MODE = 0b0000001000000000
RDA_SEEK_TH_OLD = 0b0000000011111100
RDA_BLEND_EN = 0b0000000000000010
RDA_FREQ_MODE = 0b0000000000000001

# REG 0x0A
RDA_RDSR = 0b1000000000000000
RDA_STC = 0b0100000000000000
RDA_SF = 0b0010000000000000
RDA_RDSS = 0b0001000000000000
RDA_BLK_E = 0b0000100000000000
RDA_ST = 0b0000010000000000
RDA_READCHAN = 0b0000001111111111

# REG 0x0B
RDA_RSSI = 0b1111110000000000
RDA_FM_TRUE = 0b0000001000000000
RDA_FM_READY = 0b0000000100000000
RDA_ABCD_E = 0b0000000000010000
RDA_BLERA = 0b0000000000001100
RDA_BLERB = 0b0000000000000011

# ========

RDS_GROUP_TYPE_CODE = 0xf000
RDS_PTY = 0x03e0
RDS_B0 = 0x0800


class Rda5807m:

    def __init__(self, bus):
        # Create I2C device.
        self.pi = pigpio.pi()
        self.read_handle = self.pi.i2c_open(bus, RDA_I2C_READ_ADDRESS)
        self.write_handle = self.pi.i2c_open(bus, RDA_I2C_WRITE_ADDRESS)

        self.out_buffer = [0] * 12
        self.read_bug = False

        self.rds_init()

    def read_chip(self, reg):
        data = self.pi.i2c_read_word_data(self.read_handle, reg)
        if self.read_bug:
            return (data >> 8) + ((data & 0xff) << 8)
        else:
            return data

    def write_chip(self, count):
        self.pi.i2c_write_device(self.write_handle, bytes(self.out_buffer[:count]))

    def init_chip(self):
        data = self.read_chip(0)
        found = False
        if data >> 8 == RDA_CHIP_ID:
            found = True
            self.read_bug = False
        elif data & 0xff == RDA_CHIP_ID:
            found = True
            self.read_bug = True
        if not found:
            raise Exception("i2c device not found")

        if self.read_chip(13) == 0x5804 and self.read_chip(15) == 0x5804:
            # device not already used, initialize it
            self.on()

    def write_setting(self):
        # REG 02 - normal output, enable mute, stereo, no bass boost
        # clock = 32.768KHZ, RDS enabled, new demod method, power on
        data = RDA_DHIZ | RDA_32_768KHZ | RDA_RDS_EN | RDA_NEW_METHOD | RDA_ENABLE
        self.out_buffer[0] = data >> 8
        self.out_buffer[1] = data & 0xff
        # REG 03 - no auto tune, 87-108 band, 0.1 spacing
        data = (RDA_TUNE & 0) | RDA_87_108MHZ | RDA_100KHZ
        self.out_buffer[2] = data >> 8
        self.out_buffer[3] = data & 0xff
        # REG 04 - audio 50US, no soft mute, disable AFC
        data = RDA_50US | RDA_AFCD
        self.out_buffer[4] = data >> 8
        self.out_buffer[5] = data & 0xff
        # REG 05 - mid volume
        data = RDA_INT_MODE | 0x0880 | (RDA_VOLUME >> 1)
        self.out_buffer[6] = data >> 8
        self.out_buffer[7] = data & 0xff
        # REG 06 - reserved
        self.out_buffer[8] = 0
        self.out_buffer[9] = 0
        # REG 07
        blend_threshold = 0b0011110000000000  # mix L+R with falling signal strength
        data = blend_threshold | RDA_65_50M_MODE | 0x80 | 0x40 | RDA_BLEND_EN
        self.out_buffer[10] = data >> 8
        self.out_buffer[11] = data & 0xff

    def write_tune(self, value):
        data = ((self.out_buffer[2] << 8) | self.out_buffer[3]) | RDA_TUNE
        if not value:
            data = data ^ RDA_TUNE
        self.out_buffer[2] = data >> 8
        self.out_buffer[3] = data & 0xff

    def write_from_chip(self):
        for loop in range(2, 8):
            data = self.read_chip(loop)
            self.out_buffer[(loop * 2) - 4] = data >> 8
            self.out_buffer[(loop * 2) - 3] = data & 0xff
        self.write_tune(False)  # disable tuning

    WRITE_METHODS = {
        "off": {"reg": 2, "mask": RDA_ENABLE, "how": "flag", "left-shift": 0},
        "dmute": {"reg": 2, "mask": RDA_DMUTE, "how": "flag", "left-shift": 0},
        "mono": {"reg": 2, "mask": RDA_MONO, "how": "flag", "left-shift": 0},
        "bass": {"reg": 2, "mask": RDA_BASS, "how": "flag", "left-shift": 0},
        "seekup": {"reg": 2, "mask": RDA_SEEKUP, "how": "flag", "left-shift": 0},
        "seek": {"reg": 2, "mask": RDA_SEEK, "how": "flag", "left-shift": 0},
        "skmode": {"reg": 2, "mask": RDA_SKMODE, "how": "flag", "left-shift": 0},
        "de": {"reg": 4, "mask": RDA_DE, "how": "value", "left-shift": 0},
        "volume": {"reg": 5, "mask": RDA_VOLUME, "how": "value", "left-shift": 0},
        "chan": {"reg": 3, "mask": RDA_CHAN, "how": "value", "left-shift": 6},
    }

    READ_METHODS = {
        "dmute": {"reg": 2, "mask": RDA_DMUTE, "right-shift": 0},
        "bass": {"reg": 2, "mask": RDA_BASS, "right-shift": 0},
        "mono": {"reg": 2, "mask": RDA_MONO, "right-shift": 0},
        "band": {"reg": 3, "mask": RDA_BAND, "right-shift": 0},
        "space": {"reg": 3, "mask": RDA_SPACE, "right-shift": 0},
        "de": {"reg": 4, "mask": RDA_DE, "right-shift": 0},
        "volume": {"reg": 5, "mask": RDA_VOLUME, "right-shift": 0},
        "st": {"reg": 10, "mask": RDA_ST, "right-shift": 0},
        "rssi": {"reg": 11, "mask": RDA_RSSI, "right-shift": 10},
    }

    def __getattr__(self, name):
        parts = name.split('_')
        if len(parts) != 2 or parts[0] not in ["read", "write"]:
            raise AttributeError("attribute '%s' not found" % (name,))
        name = parts[1]
        if parts[0] == "read":
            if name in self.READ_METHODS:
                params = self.READ_METHODS[name]
                return partial(
                    self.read_param,
                    params["reg"],
                    params["mask"],
                    params["right-shift"]
                )
        elif parts[0] == "write":
            if name in self.WRITE_METHODS:
                params = self.WRITE_METHODS[name]
                return partial(
                    self.write_param,
                    params["reg"],
                    params["mask"],
                    params["how"],
                    params["left-shift"]
                )
        raise AttributeError("attribute '%s' not found" % (name,))

    def read_param(self, reg, mask, right_shift):
        return (self.read_chip(reg) & mask) >> right_shift

    def write_param(self, reg, mask, how, left_shift, value):
        data = (self.read_chip(reg) | mask) ^ mask
        if how == "flag":
            if value:
                data = data | mask
        elif how == "value":
            value <<= left_shift
            data = data | value
        out_reg = (reg - 2) * 2
        self.out_buffer[out_reg] = data >> 8
        self.out_buffer[out_reg + 1] = data & 0xff

    def set_frequency(self, freq_request):
        data = self.read_band()
        if data == RDA_87_108MHZ:
            start_freq = 870
        elif data == RDA_76_108MHZ:
            start_freq = 760
        elif data == RDA_76_91MHZ:
            start_freq = 760
        elif data == RDA_65_76MHZ:
            start_freq = 650

        data = self.read_space()
        if data == RDA_200KHZ:
            spacing = 0
        elif data == RDA_100KHZ:
            spacing = 1
        elif data == RDA_50KHZ:
            spacing = 2
        elif data == RDA_25KHZ:
            spacing = 4

        if spacing > 0:
            new_freq = (freq_request - start_freq) * spacing
        else:
            new_freq = int((freq_request - start_freq) / 2)

        self.write_dmute(True)
        self.write_chan(new_freq)
        self.write_tune(True)
        self.write_chip(4)

    def on(self):
        self.write_setting()
        self.write_chip(12)

    def off(self):
        self.write_off(False)
        self.write_chip(2)

    def set_mute(self, mute):
            self.write_dmute(not mute)
            self.write_chip(2)

    def set_volume(self, volume):
        self.write_from_chip()
        self.write_volume(volume)
        self.write_chip(8)

    def set_bass(self, bass):
            self.write_bass(bass)
            self.write_chip(2)

    def set_stereo(self, stereo):
            self.write_mono(not stereo)
            self.write_chip(2)

    def set_deemphasis(self, deemphasis):
        self.write_from_chip()
        if deemphasis == 50:
            self.write_de(RDA_50US)
        else:
            self.write_de(RDA_75US)
        self.write_chip(6)

    def set_seek(self, seek_up):
            self.write_seekup(seek_up)
            self.write_chip(2)
            self.write_seek(True)
            self.write_chip(2)

    def get_infos(self):
        data3 = self.read_chip(3)
        data10 = self.read_chip(10)
        data11 = self.read_chip(11)

        infos = {}
        infos["tune-ok"] = (data10 & RDA_STC) != 0
        infos["seek-fail"] = (data10 & RDA_SF) != 0
        infos["rds-synchro"] = (data10 & RDA_RDSS) != 0
        infos["stereo"] = (data10 & RDA_ST) != 0

        chan = data10 & RDA_READCHAN
        space = data3 & RDA_SPACE
        if space == RDA_200KHZ:
            space0 = 0.2
        elif space == RDA_100KHZ:
            space0 = 0.1
        elif space == RDA_50KHZ:
            space0 = 0.05
        elif space == RDA_25KHZ:
            space0 = 0.025
        band = data3 & RDA_BAND
        if band == RDA_87_108MHZ:
            band0 = 87.0
        elif RDA_76_91MHZ:
            band0 = 76.0
        elif RDA_76_108MHZ:
            band0 = 76.0
        elif RDA_65_76MHZ:
            band0 = 65.0
        infos["freq"] = band0 + chan * space0

        signal = (data11 & RDA_RSSI) >> 10
        infos["signal"] = "%.1f" % ((signal * 100) / 64,)
        infos["fm-station"] = (data11 & RDA_FM_READY) != 0
        infos["fm-true"] = (data11 & RDA_FM_TRUE) != 0

        infos["PS"] = self.station_name
        infos["PTY"] = self.pty
        infos["Text"] = self.text
        infos["CTime"] = self.ctime
        return infos

    def rds_init(self):
        self.pty = 0
        self.station_name = "--------"
        self.station_name_tmp_1 = ['-'] * 8
        self.station_name_tmp_2 = ['-'] * 8
        self.text = '-' * 64
        self.text_tmp = ['-'] * 64
        self.ab = False
        self.idx = 0
        self.ctime = ""

    def process_rds(self):
        reg_a = self.read_chip(10)
        if reg_a & RDA_RDSS == 0:
            self.rds_init()
        reg_b = self.read_chip(11)
        if reg_a & RDA_RDSR == 0 or reg_b & RDA_BLERB != 0:
            # no new rds group ready
            return

        self.read_chip(12)
        block_b = self.read_chip(13)
        block_c = self.read_chip(14)
        block_d = self.read_chip(15)

        self.pty = (block_b & RDS_PTY) >> 5

        group_type = 0x0a + ((block_b & RDS_GROUP_TYPE_CODE) >> 8) | ((block_b & RDS_B0) >> 11)

        if group_type in [0x0a, 0x0b]:
            # PS name
            idx = (block_b & 3) * 2
            c1 = chr(block_d >> 8)
            c2 = chr(block_d & 0xff)
            if c1 in printable and c2 in printable:
                if self.station_name_tmp_1[idx:idx + 2] == [c1, c2]:
                    self.station_name_tmp_2[idx:idx + 2] = [c1, c2]
                    if self.station_name_tmp_1 == self.station_name_tmp_2:
                        self.station_name = ''.join(self.station_name_tmp_1)
                if self.station_name_tmp_1[idx:idx + 2] != [c1, c2]:
                    self.station_name_tmp_1[idx:idx + 2] = [c1, c2]

        elif group_type == 0x2a:
            # Text
            idx = (block_b & 0x0f) * 4
            if idx < self.idx:
                self.text = ''.join(self.text_tmp)
            self.idx = idx

            ab = (block_b & 0x10) != 0
            if ab != self.ab:
                self.text = '-' * 64
                self.text_tmp = ['-'] * 64
                self.ab = ab

            c1 = chr(block_c >> 8)
            c2 = chr(block_c & 0xff)
            c3 = chr(block_d >> 8)
            c4 = chr(block_d & 0xff)
            if c1 in printable and c2 in printable and c3 in printable and c4 in printable:
                self.text_tmp[idx:idx + 4] = [c1, c2, c3, c4]

        elif group_type == 0x4a:
            offset = block_d & 0x1f
            mins = (block_d & 0x0fc0) >> 6
            hour = ((block_c & 1) << 4) | (block_d >> 12)
            mins += 60 * hour
            if block_d & 0x20:
                mins -= 30 * offset
            else:
                mins += 30 * offset
            if 0 < mins < 1500:
                self.ctime = "CT %2d:%2d" % (int(mins / 60), mins % 60)

    def close(self):
        self.pi.i2c_close(self.read_handle)
        self.pi.i2c_close(self.write_handle)
        self.pi.stop()
