import smbus2
import math
class Compass:
    def __init__(self, i2c_bus=7, address=0x1E):
        self.bus = smbus2.SMBus(i2c_bus)
        self.address = address
        self.initialize()

    def initialize(self):
        # Example config for HMC5883L
        self.bus.write_byte_data(self.address, 0x00, 0x70)  # Config A
        self.bus.write_byte_data(self.address, 0x01, 0xA0)  # Config B
        self.bus.write_byte_data(self.address, 0x02, 0x00)  # Continuous mode

    def read_raw(self):
        data = self.bus.read_i2c_block_data(self.address, 0x03, 6)
        x = self._twos_complement(data[0] << 8 | data[1])
        z = self._twos_complement(data[2] << 8 | data[3])
        y = self._twos_complement(data[4] << 8 | data[5])
        return (x, y, z)

    def get_heading(self):
        x, y, _ = self.read_raw()
        heading_rad = math.atan2(y, x)
        if heading_rad < 0:
            heading_rad += 2 * math.pi
        return heading_rad

    def _twos_complement(self, val):
        return val - 65536 if val >= 32768 else val
