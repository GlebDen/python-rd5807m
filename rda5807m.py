# -*- coding: utf8 -*-

# RDA5807M Radio App for Raspberry Pi
# C version - redhawk 04/04/2014
# Python version version - Franck Barbenoire 17/03/2016
#
# This code is provided to help with programming the RDA chip.

import pigpio

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


class Rda5807m:

    def __init__(self, bus):
        # Create I2C device.
        self.pi = pigpio.pi()
        self.read_handle = self.pi.i2c_open(bus, RDA_I2C_READ_ADDRESS)
        self.write_handle = self.pi.i2c_open(bus, RDA_I2C_WRITE_ADDRESS)

        self.out_buffer = [0] * 12
        self.read_bug = False

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
            self.write_setting()
            self.write_chip(12)

    def write_setting(self):
        # REG 02
        # normal output, enable mute, stereo, no bass boost
        # clock = 32.768KHZ, RDS enabled, new demod method, power on
        data = RDA_DHIZ | RDA_32_768KHZ | RDA_RDS_EN | \
            RDA_NEW_METHOD | RDA_ENABLE
        self.out_buffer[0] = data >> 8
        self.out_buffer[1] = data & 0xff
        # REG 03 - no auto tune, 76-108 band, 0.1 spacing
        data = (RDA_TUNE & 0) | RDA_76_108MHZ | RDA_100KHZ
        self.out_buffer[2] = data >> 8
        self.out_buffer[3] = data & 0xff
        # REG 04 - audio 50US, no soft mute, disable AFC
        data = RDA_50US | RDA_AFCD
        self.out_buffer[4] = data >> 8
        self.out_buffer[5] = data & 0xff
        # REG 05 - max volume
        data = RDA_INT_MODE | 0x0880 | RDA_VOLUME
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

    def write_off(self):
        data = (self.read_chip(2) | RDA_ENABLE) ^ RDA_ENABLE
        self.out_buffer[0] = data >> 8
        self.out_buffer[1] = data & 0xff

    def write_dmute(self, value):
        data = (self.read_chip(2) | RDA_DMUTE)
        if value == 0:
            data = data ^ RDA_DMUTE
        self.out_buffer[0] = data >> 8
        self.out_buffer[1] = data & 0xff

    def write_mono(self, value):
        data = (self.read_chip(2) | RDA_MONO)
        if value == 0:
            data = data ^ RDA_MONO
        self.out_buffer[0] = data >> 8
        self.out_buffer[1] = data & 0xff

    def write_bass(self, value):
        data = (self.read_chip(2) | RDA_BASS)
        if value == 0:
            data = data ^ RDA_BASS
        self.out_buffer[0] = data >> 8
        self.out_buffer[1] = data & 0xff

    def write_chan(self, value):
        data = (self.read_chip(3) | RDA_CHAN) ^ RDA_CHAN
        self.out_buffer[2] = (value >> 2) | (data >> 8)
        self.out_buffer[3] = (value << 6) | (data & 0xff)

    def write_tune(self, value):
        data = ((self.out_buffer[2] << 8) | self.out_buffer[3]) | RDA_TUNE
        if value == 0:
            data = data ^ RDA_TUNE
        self.out_buffer[2] = data >> 8
        self.out_buffer[3] = data & 0xff

    def write_de(self, value):
        data = (self.read_chip(4) | RDA_DE) ^ RDA_DE
        if value == 0:
            data = data | RDA_50US
        if value == 1:
            data = data | RDA_75US
        self.out_buffer[4] = data >> 8
        self.out_buffer[5] = data & 0xff

    def write_volume(self, value):
        data = (self.read_chip(5) | RDA_VOLUME) ^ RDA_VOLUME
        if value > RDA_VOLUME:
            value = RDA_VOLUME
        data = data | value
        self.out_buffer[6] = data >> 8
        self.out_buffer[7] = data & 0xff

    def write_from_chip(self):
        for loop in range(2, 8):
            data = self.read_chip(loop)
            self.out_buffer[(loop * 2) - 4] = data >> 8
            self.out_buffer[(loop * 2) - 3] = data & 0xff
        self.write_tune(0)  # disable tuning

    def read_dmute(self):
        data = 0
        data = self.read_chip(2) & RDA_DMUTE
        return data

    def read_mono(self):
        data = 0
        data = self.read_chip(2) & RDA_MONO
        return data

    def read_bass(self):
        data = 0
        data = self.read_chip(2) & RDA_BASS
        return data

    def read_band(self):
        data = 0
        data = self.read_chip(3) & RDA_BAND
        return data

    def read_space(self):
        data = 0
        data = self.read_chip(3) & RDA_SPACE
        return data

    def read_de(self):
        data = 0
        data = self.read_chip(4) & RDA_DE
        return data

    def read_volume(self):
        data = 0
        data = self.read_chip(5) & RDA_VOLUME
        return data

    def read_st(self):
        data = 0
        data = self.read_chip(10) & RDA_ST
        return data

    def read_rssi(self):
        data = 0
        data = (self.read_chip(11) & RDA_RSSI) >> 10
        return data

    def set_frequency(self, freq_request):
        # data = self.read_setting("band")
        data = self.read_band()
        if data == RDA_87_108MHZ:
            start_freq = 870
        elif data == RDA_76_108MHZ:
            start_freq = 760
        elif data == RDA_76_91MHZ:
            start_freq = 760
        elif data == RDA_65_76MHZ:
            start_freq = 650
        # data = self.read_setting("space")
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
        self.write_dmute(1)
        self.write_chan(new_freq)
        self.write_tune(1)
        self.write_chip(4)

    def off(self):
        self.write_off()
        self.write_chip(2)

    def set_mute(self, mute):
        if mute:
            self.write_dmute(0)
            self.write_chip(2)
        else:
            self.write_dmute(1)
            self.write_chip(2)

    def set_volume(self, volume):
        self.write_from_chip()
        self.write_volume(volume)
        self.write_chip(8)

    def set_bass(self, bass):
        if bass:
            self.write_bass(1)
            self.write_chip(2)
        else:
            self.write_bass(0)
            self.write_chip(2)

    def set_stereo(self, stereo):
        if stereo:
            self.write_mono(0)
            self.write_chip(2)
        else:
            self.write_mono(1)
            self.write_chip(2)

    def set_deemphasis(self, deemphasis):
        self.write_from_chip()
        if deemphasis == 75:
            self.write_de(1)
            self.write_chip(6)
        else:
            self.write_de(0)
            self.write_chip(6)

    def close(self):
        self.pi.i2c_close(self.read_handle)
        self.pi.i2c_close(self.write_handle)
        self.pi.stop()
