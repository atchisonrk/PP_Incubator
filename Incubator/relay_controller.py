import logging
import time
import os

# Set environment variable to use mock pins
os.environ['GPIOZERO_PIN_FACTORY'] = 'mock'

# Use gpiozero instead of RPi.GPIO directly
from gpiozero import DigitalOutputDevice

logger = logging.getLogger('incubator.relay')

class RelayController:
    """
    Class to control relays connected to Raspberry Pi GPIO pins.
    
    Note: This implementation uses active-high configuration as requested:
    - GPIO HIGH (1) turns the relay ON
    - GPIO LOW (0) turns the relay OFF
    """
    
    # Define relay channels and corresponding GPIO pins
    HEATER1 = 0    # GPIO pin 17
    HEATER2 = 1    # GPIO pin 18
    HUMIDIFIER = 2 # GPIO pin 27
    
    # Additional relays (if used in future)
    RELAY4 = 3     # GPIO pin 22
    RELAY5 = 4     # GPIO pin 23
    RELAY6 = 5     # GPIO pin 24
    RELAY7 = 6     # GPIO pin 25
    RELAY8 = 7     # GPIO pin 4
    
    def __init__(self):
        """Initialize the GPIO pins for relay control."""
        # Map relay channels to GPIO pins
        self.relay_pins = {
            self.HEATER1: 17,
            self.HEATER2: 18,
            self.HUMIDIFIER: 27,
            self.RELAY4: 22,
            self.RELAY5: 23,
            self.RELAY6: 24,
            self.RELAY7: 25,
            self.RELAY8: 4
        }
        
        # Set up all relay pins as outputs using gpiozero
        # Using active_high=True as requested by the user (HIGH = ON, LOW = OFF)
        self.relay_devices = {}
        for channel, pin in self.relay_pins.items():
            # Create a digital output device with initial value of False (LOW = relay OFF)
            # active_high=True means that the output is considered "on" when the pin is HIGH
            self.relay_devices[channel] = DigitalOutputDevice(pin, active_high=True, initial_value=False)
            # Now the relay is OFF - set_value(True) will turn it ON, set_value(False) will turn it OFF
        
        # Track relay states (True = ON, False = OFF)
        self.relay_states = {
            self.HEATER1: False,
            self.HEATER2: False,
            self.HUMIDIFIER: False,
            self.RELAY4: False,
            self.RELAY5: False,
            self.RELAY6: False,
            self.RELAY7: False,
            self.RELAY8: False
        }
        
        logger.info("Relay controller initialized with all relays OFF")

    def turn_on_relay(self, relay_channel):
        """
        Turn ON a specific relay.
        
        Args:
            relay_channel: The relay channel to turn on
        """
        if relay_channel not in self.relay_devices:
            raise ValueError(f"Invalid relay channel: {relay_channel}")
        
        # Turn ON the relay using gpiozero (on = True for active_high=True)
        self.relay_devices[relay_channel].on()
        self.relay_states[relay_channel] = True
        pin = self.relay_pins[relay_channel]
        logger.info(f"Relay channel {relay_channel} turned ON (Pin {pin})")

    def turn_off_relay(self, relay_channel):
        """
        Turn OFF a specific relay.
        
        Args:
            relay_channel: The relay channel to turn off
        """
        if relay_channel not in self.relay_devices:
            raise ValueError(f"Invalid relay channel: {relay_channel}")
        
        # Turn OFF the relay using gpiozero (off = False for active_high=True)
        self.relay_devices[relay_channel].off()
        self.relay_states[relay_channel] = False
        pin = self.relay_pins[relay_channel]
        logger.info(f"Relay channel {relay_channel} turned OFF (Pin {pin})")

    def toggle_relay(self, relay_channel):
        """
        Toggle a specific relay (ON->OFF or OFF->ON).
        
        Args:
            relay_channel: The relay channel to toggle
        """
        if self.relay_states[relay_channel]:
            self.turn_off_relay(relay_channel)
        else:
            self.turn_on_relay(relay_channel)
            
    def get_relay_state(self, relay_channel):
        """
        Get the current state of a specific relay.
        
        Args:
            relay_channel: The relay channel to check
        
        Returns:
            bool: True if relay is ON, False if OFF
        """
        if relay_channel not in self.relay_states:
            raise ValueError(f"Invalid relay channel: {relay_channel}")
        
        return self.relay_states[relay_channel]

    def turn_off_all_relays(self):
        """Turn OFF all relays."""
        for channel in self.relay_pins:
            self.turn_off_relay(channel)
        logger.info("All relays turned OFF")

    def cleanup(self):
        """
        Clean up GPIO resources. Should be called when program exits.
        """
        # Make sure all relays are turned off first
        self.turn_off_all_relays()
        time.sleep(0.1)  # Small delay to ensure relays have time to respond
        
        # Close all devices
        for device in self.relay_devices.values():
            device.close()
        
        logger.info("GPIO cleanup completed")


# Simple test code that runs if this file is executed directly
if __name__ == "__main__":
    # Set up logging for standalone test
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create relay controller
    controller = RelayController()
    
    try:
        # Test cycle through each relay
        print("Testing relays - turning each ON for 2 seconds")
        for relay in [RelayController.HEATER1, RelayController.HEATER2, 
                      RelayController.HUMIDIFIER]:
            controller.turn_on_relay(relay)
            time.sleep(2)
            controller.turn_off_relay(relay)
            time.sleep(1)
            
        print("Relay test completed")
        
    except KeyboardInterrupt:
        print("Test interrupted")
    finally:
        # Clean up
        controller.cleanup()
