# PurePeck Incubator Controller

A Flask-based incubator control system for Raspberry Pi that provides precise environmental monitoring and management for critical temperature and humidity control.

## Key Features

- Real-time temperature and humidity tracking using SHT30 sensor
- Dual independent auto-control systems for temperature and humidity
- Configurable relay controls for heaters and humidifier
- Emergency safety features with manual override capabilities
- Analytics dashboard with historical data (up to 21 days)
- Mobile-friendly web interface accessible on local network

## Hardware Requirements

- Raspberry Pi (3B+ or 4 recommended)
- SHT30 temperature/humidity sensor (connected via I2C)
- 8-channel relay board connected to GPIO pins
- Heaters (connected to relays 1 and 2)
- Humidifier (connected to relay 3)
- Overheat safety sensor (connected to GPIO 26)

## GPIO Pin Configuration

- Heater 1: GPIO 17
- Heater 2: GPIO 18
- Humidifier: GPIO 27
- Overheat Safety Sensor: GPIO 26
- (Additional relays are configured but unused: GPIO 22, 23, 24, 25, 4)

## Installation Instructions

1. Install required packages:
   ```
   sudo apt update
   sudo apt install python3-pip python3-flask python3-gpiozero python3-smbus i2c-tools git
   ```

2. Enable I2C interface:
   ```
   sudo raspi-config
   ```
   Navigate to "Interfacing Options" > "I2C" and enable it.

3. Clone the repository:
   ```
   git clone https://github.com/yourusername/purepeck-incubator.git
   cd purepeck-incubator
   ```

4. Install Python dependencies:
   ```
   pip3 install -r requirements.txt
   ```

5. Set up the systemd service for auto-start:
   ```
   sudo cp incubator.service /etc/systemd/system/
   sudo systemctl enable incubator
   sudo systemctl start incubator
   ```

## Access the Interface

The web interface will be available at:
```
http://[your-pi-ip-address]:5000
```

Default login credentials:
- Username: admin
- Password: incubator2025

(It's recommended to change these after first login)

## Usage

1. **Dashboard**: Shows real-time temperature and humidity with device status
2. **Control Panel**: Allows manual control of heaters and humidifier
3. **Auto Control**: Set target temperature and humidity for automatic management
4. **Analytics**: View historical data with customizable time periods

## Safety Features

- Automatic emergency shutdown if overheat sensor is triggered
- Manual emergency shutdown button
- Automatic logging of all device operations
- Sequential heating (heater 2 only activates if heater 1 has been on for 3 minutes)
- Temperature control range limited to 95.0°F - 102.0°F for safety

## Maintenance

- Log files are stored in the `logs` directory
- Data files are stored in the `data` directory (CSV format)
- Old data is automatically purged after 21 days