import os
import logging
import time
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
import threading

# Import our custom modules
from relay_controller import RelayController
from sensor_reader import SensorReader
from emergency_handler import EmergencyHandler
from data_logger import DataLogger

# Set up logging
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/incubator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('incubator')

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "incubator_secret_key")

# Configuration settings
SAFE_TEMP_LOW = 95.0   # °F
SAFE_TEMP_HIGH = 102.0  # °F
SAFE_HUMIDITY_LOW = 40.0  # %
SAFE_HUMIDITY_HIGH = 70.0  # %

# Default target values
app.config['TARGET_TEMPERATURE'] = 99.5  # °F
app.config['TARGET_HUMIDITY'] = 55.0  # %

# Hardcoded credentials (insecure, but acceptable per requirements)
USERNAME = "admin"
PASSWORD = "incubator123"

# Initialize hardware controllers
try:
    relay_controller = RelayController()
    sensor_reader = SensorReader()
    emergency_handler = EmergencyHandler(relay_controller)
    
    # Set up emergency handler with callback for the overheat sensor
    emergency_handler.setup_overheat_monitoring()
    
    # Initialize data logger for analytics
    data_logger = DataLogger(data_dir='data', retention_days=21)
    
    logger.info("Hardware controllers initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize hardware controllers: {e}")
    # In a real scenario, we might want to exit or fail gracefully
    # For now, we'll continue but many functions will not work properly

# Global state variables
incubator_state = {
    "temperature": 0.0,
    "humidity": 0.0,
    "heater1_on": False,
    "heater2_on": False,
    "humidifier_on": False,
    "is_overheat": False,
    "last_updated": time.time(),
    "alerts": [],
    "target_temperature": app.config['TARGET_TEMPERATURE'],
    "target_humidity": app.config['TARGET_HUMIDITY']
}

# Flag to control monitoring thread
monitor_running = True

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Monitoring thread function
def monitor_sensors():
    global monitor_running
    logger.info("Starting sensor monitoring thread")
    
    while monitor_running:
        try:
            # Try to read temperature and humidity from sensor
            try:
                temp, humidity = sensor_reader.read_sensor()
            except Exception as e:
                # Handle sensor read errors
                error_msg = str(e)
                logger.error(f"Sensor error: {error_msg}")
                # Add error to alerts
                incubator_state["alerts"].append({"type": "danger", "message": f"Sensor error: {error_msg}"})
                # Set default values to indicate error state
                temp = 0
                humidity = 0
                
            # Check overheat condition with extra safeguards
            try:
                is_overheat = emergency_handler.check_overheat()
            except Exception as e:
                logger.error(f"Error checking overheat status: {e}")
                is_overheat = False  # Assume safe if check fails
            
            # Update global state
            incubator_state["temperature"] = temp
            incubator_state["humidity"] = humidity
            incubator_state["is_overheat"] = is_overheat
            incubator_state["last_updated"] = time.time()
            
            # Clear old alerts if sensor is working
            if temp > 0 or humidity > 0:
                incubator_state["alerts"] = []
            
            # Only check environmental alerts if sensors are working (not giving zero readings)
            if temp > 0:
                # Check for temperature alerts
                if temp < SAFE_TEMP_LOW:
                    alert = f"WARNING: Temperature too low ({temp:.1f}°F)"
                    incubator_state["alerts"].append({"type": "warning", "message": alert})
                    logger.warning(alert)
                elif temp > SAFE_TEMP_HIGH:
                    alert = f"WARNING: Temperature too high ({temp:.1f}°F)"
                    incubator_state["alerts"].append({"type": "warning", "message": alert})
                    logger.warning(alert)
            
            if humidity > 0:
                # Check for humidity alerts
                # Only show humidity alerts if humidifier is on or if humidity is too high
                # This prevents low humidity warnings when humidifier is deliberately off
                if incubator_state["humidifier_on"] and humidity < SAFE_HUMIDITY_LOW:
                    alert = f"WARNING: Humidity too low ({humidity:.1f}%)"
                    incubator_state["alerts"].append({"type": "warning", "message": alert})
                    logger.warning(alert)
                elif humidity > SAFE_HUMIDITY_HIGH:
                    alert = f"WARNING: Humidity too high ({humidity:.1f}%)"
                    incubator_state["alerts"].append({"type": "warning", "message": alert})
                    logger.warning(alert)
                
            # Check for overheat emergency
            if is_overheat:
                alert = "EMERGENCY: Overheat detected! Heaters disabled."
                incubator_state["alerts"].append({"type": "danger", "message": alert})
                logger.error(alert)
                
                # Turn off heaters for safety
                relay_controller.turn_off_relay(RelayController.HEATER1)
                relay_controller.turn_off_relay(RelayController.HEATER2)
                incubator_state["heater1_on"] = False
                incubator_state["heater2_on"] = False
            
            # Update relay states
            incubator_state["heater1_on"] = relay_controller.get_relay_state(RelayController.HEATER1)
            incubator_state["heater2_on"] = relay_controller.get_relay_state(RelayController.HEATER2)
            incubator_state["humidifier_on"] = relay_controller.get_relay_state(RelayController.HUMIDIFIER)
            
            # Log data periodically (every minute)
            if int(time.time()) % 60 < 5:  # Log approximately every minute
                logger.info(f"Status: Temp={temp:.1f}°F, Humidity={humidity:.1f}%, " +
                           f"Heater1={'ON' if incubator_state['heater1_on'] else 'OFF'}, " +
                           f"Heater2={'ON' if incubator_state['heater2_on'] else 'OFF'}, " +
                           f"Humidifier={'ON' if incubator_state['humidifier_on'] else 'OFF'}")
                
                # Log data to CSV file for analytics
                data_logger.log_data(
                    temperature=temp,
                    humidity=humidity,
                    heater1_on=incubator_state["heater1_on"],
                    heater2_on=incubator_state["heater2_on"],
                    humidifier_on=incubator_state["humidifier_on"],
                    target_temperature=incubator_state["target_temperature"],
                    target_humidity=incubator_state["target_humidity"]
                )
                
                # Purge old data files (older than 21 days)
                data_logger.purge_old_data()
                
        except Exception as e:
            logger.error(f"Error in monitoring thread: {e}")
            incubator_state["alerts"].append({"type": "danger", "message": f"Sensor error: {str(e)}"})
            
        # Wait before next reading
        time.sleep(5)  # Check sensors every 5 seconds

# Routes
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == USERNAME and password == PASSWORD:
            session['logged_in'] = True
            logger.info(f"User '{username}' logged in successfully")
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')
            logger.warning(f"Failed login attempt for user '{username}'")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/analytics')
@login_required
def analytics():
    return render_template('analytics.html')

@app.route('/api/analytics')
@login_required
def api_analytics():
    """
    API endpoint to fetch historical analytics data for charts and stats.
    """
    try:
        # Get query parameters with defaults
        days = request.args.get('days', default=1, type=int)
        interval = request.args.get('interval', default=10, type=int)
        
        # Validate parameters
        if days < 1 or days > 21:
            days = 1  # Default to 1 day if invalid
        
        if interval < 1:
            interval = 10  # Default to 10 minutes if invalid
        
        # Get data from the data logger
        data = data_logger.get_recent_data(days=days, interval_minutes=interval)
        
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error fetching analytics data: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/status')
@login_required
def api_status():
    return jsonify(incubator_state)

@app.route('/api/control', methods=['POST'])
@login_required
def api_control():
    data = request.json
    device = data.get('device')
    action = data.get('action')
    
    if not device or not action:
        return jsonify({"success": False, "message": "Missing device or action parameter"}), 400
    
    try:
        # Handle emergency shutdown
        if device == 'emergency' and action == 'shutdown':
            logger.warning("EMERGENCY SHUTDOWN triggered by user")
            emergency_handler.emergency_shutdown()
            return jsonify({"success": True, "message": "Emergency shutdown activated"})
        
        # Don't allow turning on heaters if overheat is active or if last temperature reading is stale
        if action == "on" and (device == "heater1" or device == "heater2"):
            # Check for overheat condition
            if incubator_state["is_overheat"]:
                return jsonify({
                    "success": False, 
                    "message": "Cannot turn on heaters during overheat condition"
                }), 400
                
            # Check for sensor failure/disconnection - if last reading is more than 2 minutes old
            current_time = time.time()
            if current_time - incubator_state["last_updated"] > 120:
                logger.error("SAFETY: Temperature sensor readings are stale, refusing to activate heaters")
                return jsonify({
                    "success": False, 
                    "message": "Cannot turn on heaters: Temperature sensor not responding"
                }), 400
        
        # Handle normal relay control
        if device == 'heater1':
            relay = RelayController.HEATER1
        elif device == 'heater2':
            relay = RelayController.HEATER2
        elif device == 'humidifier':
            relay = RelayController.HUMIDIFIER
        else:
            return jsonify({"success": False, "message": f"Unknown device: {device}"}), 400
        
        if action == 'on':
            relay_controller.turn_on_relay(relay)
            logger.info(f"Turned ON {device}")
        elif action == 'off':
            relay_controller.turn_off_relay(relay)
            logger.info(f"Turned OFF {device}")
        else:
            return jsonify({"success": False, "message": f"Unknown action: {action}"}), 400
        
        # Update state after control action
        if device == 'heater1':
            incubator_state["heater1_on"] = relay_controller.get_relay_state(relay)
        elif device == 'heater2':
            incubator_state["heater2_on"] = relay_controller.get_relay_state(relay)
        elif device == 'humidifier':
            incubator_state["humidifier_on"] = relay_controller.get_relay_state(relay)
            
        return jsonify({"success": True, "message": f"{device} {action} successful"})
        
    except Exception as e:
        logger.error(f"Error in control API: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/settings', methods=['POST'])
@login_required
def api_settings():
    """
    API endpoint to update settings (temperature and humidity targets)
    """
    data = request.json
    
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400
    
    setting = data.get('setting')
    value = data.get('value')
    
    if not setting or value is None:
        return jsonify({"success": False, "message": "Missing setting or value"}), 400
    
    try:
        # Update settings based on the request
        if setting == 'temperature':
            # Validate temperature range
            temp_value = float(value)
            if not (SAFE_TEMP_LOW <= temp_value <= SAFE_TEMP_HIGH):
                return jsonify({
                    "success": False, 
                    "message": f"Temperature must be between {SAFE_TEMP_LOW}°F and {SAFE_TEMP_HIGH}°F"
                }), 400
                
            # Update app config and incubator state
            app.config['TARGET_TEMPERATURE'] = temp_value
            incubator_state['target_temperature'] = temp_value
            logger.info(f"Temperature target updated to {temp_value}°F")
            
        elif setting == 'humidity':
            # Validate humidity range
            humidity_value = float(value)
            if not (SAFE_HUMIDITY_LOW <= humidity_value <= SAFE_HUMIDITY_HIGH):
                return jsonify({
                    "success": False, 
                    "message": f"Humidity must be between {SAFE_HUMIDITY_LOW}% and {SAFE_HUMIDITY_HIGH}%"
                }), 400
                
            # Update app config and incubator state
            app.config['TARGET_HUMIDITY'] = humidity_value
            incubator_state['target_humidity'] = humidity_value
            logger.info(f"Humidity target updated to {humidity_value}%")
            
        else:
            return jsonify({"success": False, "message": f"Unknown setting: {setting}"}), 400
            
        return jsonify({
            "success": True, 
            "message": f"{setting.capitalize()} target set to {value}",
            "setting": setting,
            "value": value
        })
        
    except ValueError:
        return jsonify({"success": False, "message": f"Invalid value format for {setting}"}), 400
    except Exception as e:
        logger.error(f"Error updating {setting}: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

# Flask app context setup and teardown
hardware_cleaned_up = False

# Start monitoring thread when app starts
monitor_thread = threading.Thread(target=monitor_sensors, daemon=True)
monitor_thread.start()

# Setup handler for proper cleanup when the app is stopped
import atexit

def cleanup_hardware():
    global hardware_cleaned_up, monitor_running
    if not hardware_cleaned_up:
        try:
            # First, stop the monitoring thread safely
            monitor_running = False
            time.sleep(1)  # Give thread chance to complete current cycle
            
            # Set flag to prevent double cleanup
            hardware_cleaned_up = True
            logger.info("Cleaning up hardware resources...")
            
            # Clean up in correct order - emergency handler then relay controller
            if 'emergency_handler' in globals():
                emergency_handler.cleanup()
            if 'relay_controller' in globals():
                relay_controller.cleanup()
            logger.info("Hardware resources cleaned up")
        except Exception as e:
            logger.error(f"Error during hardware cleanup: {e}")

# Register the cleanup function to be called on exit
atexit.register(cleanup_hardware)

# When Flask app context is torn down (may happen multiple times in dev mode)
@app.teardown_appcontext
def app_cleanup(error):
    if error:
        logger.error(f"Error during app teardown: {error}")

# Run the app
if __name__ == '__main__':
    logger.info("Starting incubator control app")
    app.run(host='0.0.0.0', port=5000, debug=True)
