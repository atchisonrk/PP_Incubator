"""
Data logger for the incubator controller.
Logs temperature, humidity, and device states to CSV files for analytics.
"""

import os
import csv
import time
import datetime
import logging
from threading import Lock

# Set up logging
logger = logging.getLogger('incubator.datalogger')

class DataLogger:
    """
    Class to log incubator data to CSV files for historical tracking.
    Stores data with timestamps and manages data retention.
    """
    
    # CSV column headers
    HEADERS = ['timestamp', 'temperature', 'humidity', 'heater1_on', 'heater2_on', 'humidifier_on', 
               'target_temperature', 'target_humidity']
    
    def __init__(self, data_dir='data', retention_days=21):
        """
        Initialize the data logger.
        
        Args:
            data_dir: Directory to store CSV data files
            retention_days: Number of days to retain data (older data will be purged)
        """
        self.data_dir = data_dir
        self.retention_days = retention_days
        self.lock = Lock()  # Thread safety for file operations
        
        # Ensure data directory exists
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            logger.info(f"Created data directory: {data_dir}")
        
        # Current day's file path
        self.current_file = None
        self._update_current_file()
    
    def _update_current_file(self):
        """Update the current file path based on today's date."""
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        self.current_file = os.path.join(self.data_dir, f"incubator_{today}.csv")
        
        # Create file with headers if it doesn't exist
        if not os.path.exists(self.current_file):
            with open(self.current_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(self.HEADERS)
                logger.info(f"Created new data file: {self.current_file}")
    
    def log_data(self, temperature, humidity, heater1_on, heater2_on, humidifier_on, 
                target_temperature, target_humidity):
        """
        Log a data point to the current day's CSV file.
        
        Args:
            temperature: Current temperature (float)
            humidity: Current humidity (float)
            heater1_on: Heater 1 state (bool)
            heater2_on: Heater 2 state (bool)
            humidifier_on: Humidifier state (bool)
            target_temperature: Target temperature (float)
            target_humidity: Target humidity (float)
        """
        # Make sure we're using the correct file for today
        self._update_current_file()
        
        # Current timestamp
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Prepare data row
        data = [
            timestamp, 
            f"{temperature:.1f}", 
            f"{humidity:.1f}", 
            '1' if heater1_on else '0',
            '1' if heater2_on else '0',
            '1' if humidifier_on else '0',
            f"{target_temperature:.1f}",
            f"{target_humidity:.1f}"
        ]
        
        # Safely write to file
        with self.lock:
            try:
                with open(self.current_file, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(data)
            except Exception as e:
                logger.error(f"Error logging data: {str(e)}")
    
    def purge_old_data(self):
        """Remove data files older than retention_days."""
        try:
            now = datetime.datetime.now()
            cutoff = now - datetime.timedelta(days=self.retention_days)
            
            with self.lock:
                for filename in os.listdir(self.data_dir):
                    if not filename.startswith('incubator_') or not filename.endswith('.csv'):
                        continue
                    
                    # Extract date from filename
                    try:
                        date_str = filename.replace('incubator_', '').replace('.csv', '')
                        file_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                        
                        # Delete if older than retention period
                        if file_date < cutoff:
                            file_path = os.path.join(self.data_dir, filename)
                            os.remove(file_path)
                            logger.info(f"Deleted old data file: {filename}")
                    except (ValueError, OSError) as e:
                        logger.error(f"Error processing file {filename}: {str(e)}")
        except Exception as e:
            logger.error(f"Error during data purge: {str(e)}")
    
    def get_recent_data(self, days=1, interval_minutes=10):
        """
        Get recent data for analytics, with optional downsampling.
        
        Args:
            days: Number of days of data to retrieve (int)
            interval_minutes: If >0, downsample data to this interval (minutes)
        
        Returns:
            dict: Dictionary with lists for each data column
        """
        # Initialize result structure matching what analytics.js expects
        result = {
            'timestamp': [],           # Epoch timestamps in seconds
            'temperature': [],
            'humidity': [],
            'heater1_on': [],          # Boolean values (true/false)
            'heater2_on': [], 
            'humidifier_on': [],
            'target_temperature': [],
            'target_humidity': []
        }
        
        try:
            # Calculate date range
            now = datetime.datetime.now()
            start_date = now - datetime.timedelta(days=days)
            
            # Get list of files in date range
            file_dates = []
            for i in range(days):
                date = now - datetime.timedelta(days=i)
                file_dates.append(date.strftime('%Y-%m-%d'))
            
            # Read data from each file
            all_data = []
            with self.lock:
                for date_str in file_dates:
                    file_path = os.path.join(self.data_dir, f"incubator_{date_str}.csv")
                    if not os.path.exists(file_path):
                        continue
                    
                    with open(file_path, 'r') as f:
                        reader = csv.reader(f)
                        next(reader)  # Skip header
                        for row in reader:
                            all_data.append(row)
            
            # Sort by timestamp
            all_data.sort(key=lambda x: x[0])
            
            # Apply downsampling if needed
            if interval_minutes > 0:
                downsampled_data = []
                last_sample_time = None
                
                for row in all_data:
                    try:
                        row_time = datetime.datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                        
                        if last_sample_time is None or (row_time - last_sample_time).total_seconds() >= interval_minutes * 60:
                            downsampled_data.append(row)
                            last_sample_time = row_time
                    except (ValueError, IndexError):
                        continue
                
                all_data = downsampled_data
            
            # Fill result structure
            for row in all_data:
                try:
                    # Convert timestamp string to epoch timestamp (seconds since epoch)
                    dt = datetime.datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                    epoch_time = int(dt.timestamp())
                    
                    # Add data to result structure
                    result['timestamp'].append(epoch_time)
                    result['temperature'].append(float(row[1]))
                    result['humidity'].append(float(row[2]))
                    result['heater1_on'].append(bool(int(row[3])))
                    result['heater2_on'].append(bool(int(row[4])))
                    result['humidifier_on'].append(bool(int(row[5])))
                    result['target_temperature'].append(float(row[6]))
                    result['target_humidity'].append(float(row[7]))
                except (ValueError, IndexError) as e:
                    logger.warning(f"Error processing data row: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error retrieving recent data: {str(e)}")
        
        return result