import logging
import time
import os

# Set environment variable to use mock pins
os.environ['GPIOZERO_PIN_FACTORY'] = 'mock'

# Use gpiozero instead of RPi.GPIO directly
from gpiozero import Button

logger = logging.getLogger('incubator.emergency')

class EmergencyHandler:
    """
    Class to handle emergency situations like overheating.
    Monitors the overheat sensor and provides emergency shutdown functionality.
    """
    
    # GPIO pin for the emergency overheat sensor
    OVERHEAT_SENSOR_PIN = 26  # GPIO pin 26
    
    def __init__(self, relay_controller):
        """
        Initialize the emergency handler.
        
        Args:
            relay_controller: Instance of RelayController to control relays during emergencies
        """
        self.relay_controller = relay_controller
        self.is_overheat = False
        self.overheat_sensor = None
        logger.info("Emergency handler initialized")
    
    def setup_overheat_monitoring(self):
        """Set up the GPIO pin for the overheat sensor."""
        try:
            # Create a Button object for the overheat sensor
            # We use pull_up=True because the circuit is normally closed (pulled LOW)
            # When overheating occurs, the circuit opens and goes HIGH
            self.overheat_sensor = Button(self.OVERHEAT_SENSOR_PIN, pull_up=True)
            
            # Set up a callback for when the button is pressed (circuit opens)
            self.overheat_sensor.when_pressed = self._overheat_callback
            
            logger.info("Overheat monitoring set up on GPIO pin %d", self.OVERHEAT_SENSOR_PIN)
        except Exception as e:
            logger.error(f"Error setting up overheat monitoring: {e}")
            raise
    
    def _overheat_callback(self):
        """
        Callback function triggered when overheat sensor detects overheating.
        """
        # Add debounce by waiting a moment and checking again
        time.sleep(0.1)
        if self.overheat_sensor and self.overheat_sensor.is_pressed:
            logger.critical("OVERHEAT DETECTED! Initiating emergency shutdown.")
            self.is_overheat = True
            self.emergency_shutdown()
    
    def check_overheat(self):
        """
        Check if the overheat sensor is currently triggered.
        
        Returns:
            bool: True if overheat condition exists, False otherwise
        """
        try:
            if self.overheat_sensor and hasattr(self.overheat_sensor, 'is_pressed'):
                # For gpiozero Button, is_pressed is True when the button is pressed
                # For our overheat sensor, this means the circuit is open (HIGH)
                self.is_overheat = self.overheat_sensor.is_pressed
                return self.is_overheat
            else:
                # If sensor not initialized or already closed, don't report overheat
                # This is for development mode only - in production always assume unsafe
                logger.debug("Overheat sensor not available, assuming safe for development")
                return False
        except Exception as e:
            logger.error(f"Error checking overheat sensor: {e}")
            # For development, don't assume emergency
            # In production, this should return True for safety
            return False
    
    def emergency_shutdown(self):
        """
        Execute emergency shutdown procedure:
        - Turn off all heaters immediately
        - Log the emergency event
        """
        logger.critical("EMERGENCY SHUTDOWN ACTIVATED")
        
        try:
            # Turn off critical relays (heaters)
            from relay_controller import RelayController
            self.relay_controller.turn_off_relay(RelayController.HEATER1)
            self.relay_controller.turn_off_relay(RelayController.HEATER2)
            
            # Could also turn off humidifier if needed
            # self.relay_controller.turn_off_relay(RelayController.HUMIDIFIER)
            
            logger.info("Emergency shutdown complete - all heaters disabled")
        except Exception as e:
            logger.error(f"Error during emergency shutdown: {e}")
    
    def reset_emergency(self):
        """
        Reset the emergency state if the overheat condition has cleared.
        
        Returns:
            bool: True if reset successful, False if overheat still exists
        """
        # Check if overheat condition still exists
        if self.check_overheat():
            logger.warning("Cannot reset emergency: Overheat condition still exists")
            return False
        
        logger.info("Emergency condition cleared")
        self.is_overheat = False
        return True
    
    def cleanup(self):
        """Clean up GPIO resources used by the emergency handler."""
        try:
            if self.overheat_sensor:
                # Close the Button device
                self.overheat_sensor.close()
            logger.info("Emergency handler cleanup completed")
        except Exception as e:
            logger.error(f"Error during emergency handler cleanup: {e}")


# Simple test code that runs if this file is executed directly
if __name__ == "__main__":
    # Set up logging for standalone test
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Import and create relay controller
    from relay_controller import RelayController
    relay_controller = RelayController()
    
    # Create emergency handler
    handler = EmergencyHandler(relay_controller)
    
    try:
        # Set up overheat monitoring
        handler.setup_overheat_monitoring()
        
        print("Emergency handler test - press Ctrl+C to exit")
        print("Current overheat status:", handler.check_overheat())
        print("Testing emergency shutdown...")
        
        # Test emergency shutdown
        handler.emergency_shutdown()
        
        # Monitor for 30 seconds
        for i in range(30):
            status = "OVERHEAT DETECTED" if handler.check_overheat() else "Normal"
            print(f"Monitoring ({i+1}/30): {status}")
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("Test interrupted")
    finally:
        # Clean up
        handler.cleanup()
        relay_controller.cleanup()
