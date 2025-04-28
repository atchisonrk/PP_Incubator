import time
import logging
import math
import os

try:
    import smbus2
    SMBUS_AVAILABLE = True
except ImportError:
    SMBUS_AVAILABLE = False
    print("Warning: smbus2 not available, hardware will not function")

logger = logging.getLogger('incubator.sensor')

class SensorReader:
    """
    Class to read temperature and humidity data from an SHT30 sensor 
    connected via I2C to the Raspberry Pi.
    """
    
    # SHT30 I2C address
    SHT30_ADDRESS = 0x44  # Default I2C address for SHT30
    
    # SHT30 commands
    SHT30_READ_STATUS = 0xF32D
    SHT30_CLEAR_STATUS = 0x3041
    SHT30_SOFT_RESET = 0x30A2
    SHT30_HARD_RESET = 0x0006
    SHT30_READ_HIGH_REPEATABILITY = 0x2400  # High repeatability, clock stretching disabled
    
    def __init__(self, bus_number=1):
        """
        Initialize the sensor reader.
        
        Args:
            bus_number: The I2C bus number (usually 1 for Raspberry Pi 2+)
        """
        self.initialized = False
        
        if SMBUS_AVAILABLE:
            try:
                self.bus = smbus2.SMBus(bus_number)
                
                # Reset the sensor
                self._send_command(self.SHT30_SOFT_RESET)
                time.sleep(0.05)  # Wait for reset to complete
                logger.info("SHT30 sensor initialized successfully")
                self.initialized = True
            except Exception as e:
                logger.error(f"Error initializing SHT30 sensor: {e}")
                logger.error("Hardware access failed - cannot continue without sensor")
        else:
            logger.critical("smbus2 module not available - cannot access hardware sensors")
            logger.critical("Please install required hardware libraries on your Raspberry Pi")
    
    def _send_command(self, cmd):
        """
        Send a command to the SHT30 sensor.
        
        Args:
            cmd: The command code to send
        """
        if not self.initialized:
            raise ValueError("Sensor not initialized")
            
        cmd_msb = cmd >> 8
        cmd_lsb = cmd & 0xFF
        
        self.bus.write_i2c_block_data(self.SHT30_ADDRESS, cmd_msb, [cmd_lsb])
    
    def _calculate_crc(self, data):
        """
        Calculate CRC checksum for SHT30 readings.
        
        Args:
            data: List of bytes to calculate CRC for
            
        Returns:
            int: CRC8 checksum
        """
        crc = 0xFF  # Initial value
        polynomial = 0x31  # Polynomial: x^8 + x^5 + x^4 + 1 = 0x31
        
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = ((crc << 1) ^ polynomial) & 0xFF
                else:
                    crc = (crc << 1) & 0xFF
                    
        return crc
    
    def read_sensor(self):
        """
        Read temperature and humidity from the SHT30 sensor.
        
        Returns:
            tuple: (temperature_fahrenheit, relative_humidity)
            
        Raises:
            ValueError: If sensor is not properly initialized or if reading fails
        """
        if not self.initialized:
            logger.error("Cannot read from uninitialized sensor")
            raise ValueError("Sensor not initialized or not connected")
            
        # Try to read from the sensor
        try:
            # Send measurement command
            self._send_command(self.SHT30_READ_HIGH_REPEATABILITY)
            
            # Wait for measurement to complete (15ms typical for high repeatability)
            time.sleep(0.02)
            
            # Read 6 bytes of data: temp MSB, temp LSB, temp CRC, humidity MSB, humidity LSB, humidity CRC
            data = self.bus.read_i2c_block_data(self.SHT30_ADDRESS, 0, 6)
            
            # Verify CRC checksums
            temp_data = data[0:2]
            temp_crc = data[2]
            hum_data = data[3:5]
            hum_crc = data[5]
            
            calculated_temp_crc = self._calculate_crc(temp_data)
            calculated_hum_crc = self._calculate_crc(hum_data)
            
            if temp_crc != calculated_temp_crc or hum_crc != calculated_hum_crc:
                logger.warning(f"CRC checksum failed: {temp_crc}!={calculated_temp_crc} or {hum_crc}!={calculated_hum_crc}")
                raise ValueError("CRC checksum verification failed")
            
            # Calculate temperature in Celsius
            temp_msb = data[0]
            temp_lsb = data[1]
            temp_raw = (temp_msb << 8) | temp_lsb
            temperature_c = -45 + (175 * temp_raw / 65535.0)
            
            # Convert to Fahrenheit
            temperature_f = (temperature_c * 9/5) + 32
            
            # Calculate humidity
            humidity_msb = data[3]
            humidity_lsb = data[4]
            humidity_raw = (humidity_msb << 8) | humidity_lsb
            relative_humidity = 100 * humidity_raw / 65535.0
            
            # Round to one decimal place for display
            temperature_f = round(temperature_f, 1)
            relative_humidity = round(relative_humidity, 1)
            
            # Check for values outside reasonable range
            if not (32 <= temperature_f <= 212) or not (0 <= relative_humidity <= 100):
                logger.warning(f"Sensor returned suspicious values: Temp={temperature_f}°F, Humidity={relative_humidity}%")
                # Clip to valid ranges
                temperature_f = max(32.0, min(212.0, temperature_f))
                relative_humidity = max(0.0, min(100.0, relative_humidity))
            
            return temperature_f, relative_humidity
            
        except Exception as e:
            logger.error(f"Error reading SHT30 sensor: {e}")
            # Always raise the exception on hardware error - no fallback to mock data
            raise
    
    def reset_sensor(self):
        """Reset the SHT30 sensor."""
        try:
            self._send_command(self.SHT30_SOFT_RESET)
            time.sleep(0.05)  # Wait for reset to complete
            logger.info("SHT30 sensor reset")
        except Exception as e:
            logger.error(f"Error resetting SHT30 sensor: {e}")


# Simple test code that runs if this file is executed directly
if __name__ == "__main__":
    # Set up logging for standalone test
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create sensor reader
    sensor = SensorReader()
    
    try:
        print("Reading SHT30 sensor data...")
        
        # Take 5 readings, one per second
        for i in range(5):
            temp, humidity = sensor.read_sensor()
            print(f"Reading {i+1}: Temperature = {temp}°F, Humidity = {humidity}%")
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("Test interrupted")
    except Exception as e:
        print(f"Error: {e}")
