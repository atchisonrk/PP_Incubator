// PurePeck Incubator Controller - Main JavaScript

// Global variables
let overheatingActive = false;
let updateInterval;
let lastUpdateTime = 0;
let autoTempControlEnabled = false;
let autoHumidityControlEnabled = false;
let targetTemperature = 99.5;
let targetHumidity = 55.0;
let humidityOverride = false;
let heater1StartTime = null;
let temperatureHysteresis = 0.3; // Temperature control hysteresis (±0.3°F)
let heaterSequenceEnabled = true;

// Initialize when DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Incubator controller dashboard initialized');
    
    // Setup event listeners for control buttons
    setupControlListeners();
    
    // Setup emergency shutdown button
    setupEmergencyShutdown();
    
    // Setup settings controls
    setupSettingsControls();
    
    // Setup auto control toggle
    setupAutoControlToggle();
    
    // Fetch initial status
    updateStatus();
    
    // Set up auto-refresh
    updateInterval = setInterval(updateStatus, 7000); // Update every 7 seconds
});

// Setup listeners for control switches
function setupControlListeners() {
    // Get all toggle switches
    const toggles = document.querySelectorAll('.control-toggle');
    
    // Add change event listener to each toggle
    toggles.forEach(toggle => {
        toggle.addEventListener('change', function(event) {
            const device = this.dataset.device;
            const action = this.checked ? 'on' : 'off';
            
            // Update the UI immediately (optimistic update)
            updateControlStatus(device, this.checked);
            
            // Send the control request to the server
            sendControlRequest(device, action);
        });
    });
}

// Setup emergency shutdown button
function setupEmergencyShutdown() {
    const emergencyBtn = document.getElementById('emergency-shutdown');
    
    if (emergencyBtn) {
        emergencyBtn.addEventListener('click', function(event) {
            // Ask for confirmation
            if (confirm('EMERGENCY SHUTDOWN: Are you sure you want to shut down all heating elements?')) {
                // Send emergency shutdown request
                sendControlRequest('emergency', 'shutdown');
                
                // Update UI to show all heaters as off
                document.getElementById('heater1-toggle').checked = false;
                document.getElementById('heater2-toggle').checked = false;
                
                updateControlStatus('heater1', false);
                updateControlStatus('heater2', false);
            }
        });
    }
}

// Send a control request to the server
function sendControlRequest(device, action) {
    console.log(`Sending control request: ${device} ${action}`);
    
    fetch('/api/control', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            device: device,
            action: action
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Control response:', data);
        
        if (!data.success) {
            // If control failed, show error message
            showAlert('danger', `Failed to ${action} ${device}: ${data.message}`);
            
            // Revert UI state
            setTimeout(updateStatus, 1000);
        }
    })
    .catch(error => {
        console.error('Error sending control request:', error);
        showAlert('danger', `Error controlling ${device}: ${error.message}`);
        
        // Revert UI state
        setTimeout(updateStatus, 1000);
    });
}

// Update the status display
function updateStatus() {
    fetch('/api/status')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Status update received:', data);
            
            // Get target values from the server
            if (data.target_temperature !== undefined) {
                targetTemperature = data.target_temperature;
                const currentTempTarget = document.getElementById('current-temp-target');
                if (currentTempTarget) {
                    currentTempTarget.textContent = `${targetTemperature.toFixed(1)} °F`;
                }
                
                const targetTempInput = document.getElementById('target-temp');
                if (targetTempInput) {
                    targetTempInput.value = targetTemperature;
                }
            }
            
            if (data.target_humidity !== undefined) {
                targetHumidity = data.target_humidity;
                const currentHumidityTarget = document.getElementById('current-humidity-target');
                if (currentHumidityTarget) {
                    currentHumidityTarget.textContent = `${targetHumidity.toFixed(0)} %`;
                }
                
                const targetHumidityInput = document.getElementById('target-humidity');
                if (targetHumidityInput) {
                    targetHumidityInput.value = targetHumidity;
                }
            }
            
            // Update last refresh time
            lastUpdateTime = new Date();
            document.getElementById('last-updated').textContent = formatTimestamp(lastUpdateTime);
            
            // Update temperature and humidity displays
            updateReadingDisplay('temperature', data.temperature);
            updateReadingDisplay('humidity', data.humidity);
            
            // Update control toggles state
            const heater1Toggle = document.getElementById('heater1-toggle');
            const heater2Toggle = document.getElementById('heater2-toggle');
            const humidifierToggle = document.getElementById('humidifier-toggle');
            const humidityOverrideToggle = document.getElementById('humidity-override-toggle');
            const autoToggle = document.getElementById('auto-control-toggle');
            
            // Update controls but don't trigger events
            if (heater1Toggle) {
                if (heater1Toggle.checked !== data.heater1_on) {
                    heater1Toggle.checked = data.heater1_on;
                }
                updateControlStatus('heater1', data.heater1_on);
            }
            
            if (heater2Toggle) {
                if (heater2Toggle.checked !== data.heater2_on) {
                    heater2Toggle.checked = data.heater2_on;
                }
                updateControlStatus('heater2', data.heater2_on);
            }
            
            if (humidifierToggle) {
                if (humidifierToggle.checked !== data.humidifier_on) {
                    humidifierToggle.checked = data.humidifier_on;
                }
                updateControlStatus('humidifier', data.humidifier_on);
            }
            
            // Make sure toggle states are correct
            if (autoToggle && autoToggle.checked !== autoControlEnabled) {
                autoToggle.checked = autoControlEnabled;
            }
            
            if (humidityOverrideToggle && humidityOverrideToggle.checked !== humidityOverride) {
                humidityOverrideToggle.checked = humidityOverride;
            }
            
            // Handle overheat condition
            overheatingActive = data.is_overheat;
            
            if (overheatingActive) {
                // Show overheat warning
                showOverheatWarning();
            } else {
                // Hide overheat warning if it exists
                hideOverheatWarning();
            }
            
            // Update controls availability based on current states
            updateControlsAvailability();
            
            // Display alerts
            displayAlerts(data.alerts);
        })
        .catch(error => {
            console.error('Error fetching status:', error);
            showAlert('danger', `Failed to update status: ${error.message}`);
        });
}

// Update temperature or humidity reading display
function updateReadingDisplay(type, value) {
    const element = document.getElementById(`${type}-value`);
    
    if (element) {
        // Check if value is NaN or null
        if (isNaN(value) || value === null) {
            element.textContent = 'ERROR';
            element.parentElement.classList.add('reading-error');
        } else {
            element.textContent = value.toFixed(1);
            element.parentElement.classList.remove('reading-error');
        }
    }
}

// Update control status indicator
function updateControlStatus(device, isOn) {
    const statusIndicator = document.getElementById(`${device}-status`);
    
    if (statusIndicator) {
        if (isOn) {
            statusIndicator.classList.remove('status-off');
            statusIndicator.classList.add('status-on');
        } else {
            statusIndicator.classList.remove('status-on');
            statusIndicator.classList.add('status-off');
        }
    }
}

// Display alerts
function displayAlerts(alerts) {
    const alertsContainer = document.getElementById('alerts-container');
    
    if (!alertsContainer) return;
    
    // Clear existing alerts
    alertsContainer.innerHTML = '';
    
    // Add new alerts
    if (alerts && alerts.length > 0) {
        alerts.forEach(alert => {
            const alertElement = document.createElement('div');
            alertElement.className = `alert-banner alert-${alert.type}`;
            
            alertElement.innerHTML = `
                <div class="alert-icon">
                    <i class="fas ${alert.type === 'danger' ? 'fa-exclamation-triangle' : 'fa-exclamation-circle'}"></i>
                </div>
                <div class="alert-content">
                    ${alert.message}
                </div>
            `;
            
            alertsContainer.appendChild(alertElement);
        });
    }
}

// Show overheat warning
function showOverheatWarning() {
    const alertsContainer = document.getElementById('alerts-container');
    
    // Check if overheat warning already exists
    const existingWarning = document.getElementById('overheat-warning');
    if (existingWarning) return;
    
    // Create and show overheat warning
    const warningElement = document.createElement('div');
    warningElement.className = 'alert-banner alert-danger';
    warningElement.id = 'overheat-warning';
    warningElement.style.backgroundColor = '#f8d7da';
    warningElement.style.border = '2px solid #dc3545';
    
    warningElement.innerHTML = `
        <div class="alert-icon">
            <i class="fas fa-fire"></i>
        </div>
        <div class="alert-content">
            <strong>DANGER: OVERHEATING DETECTED!</strong><br>
            Heaters have been disabled for safety. Check the incubator immediately!
        </div>
    `;
    
    if (alertsContainer) {
        alertsContainer.insertBefore(warningElement, alertsContainer.firstChild);
    }
}

// Hide overheat warning
function hideOverheatWarning() {
    const warningElement = document.getElementById('overheat-warning');
    
    if (warningElement) {
        warningElement.remove();
    }
}

// Show a temporary alert message
function showAlert(type, message) {
    const alertsContainer = document.getElementById('alerts-container');
    
    if (!alertsContainer) return;
    
    const alertElement = document.createElement('div');
    alertElement.className = `alert-banner alert-${type}`;
    alertElement.innerHTML = `
        <div class="alert-icon">
            <i class="fas ${type === 'danger' ? 'fa-exclamation-triangle' : 'fa-exclamation-circle'}"></i>
        </div>
        <div class="alert-content">
            ${message}
        </div>
    `;
    
    alertsContainer.appendChild(alertElement);
    
    // Remove after 5 seconds
    setTimeout(() => {
        alertElement.remove();
    }, 5000);
}

// Format timestamp for last updated display
function formatTimestamp(date) {
    return date.toLocaleTimeString();
}

// Setup the temperature and humidity settings controls
function setupSettingsControls() {
    // Get the elements
    const targetTempInput = document.getElementById('target-temp');
    const targetHumidityInput = document.getElementById('target-humidity');
    const setTempBtn = document.getElementById('set-temp-btn');
    const setHumidityBtn = document.getElementById('set-humidity-btn');
    const currentTempTarget = document.getElementById('current-temp-target');
    const currentHumidityTarget = document.getElementById('current-humidity-target');
    
    // Set initial values
    if (currentTempTarget) currentTempTarget.textContent = `${targetTemperature.toFixed(1)} °F`;
    if (currentHumidityTarget) currentHumidityTarget.textContent = `${targetHumidity.toFixed(0)} %`;
    
    // Set up temperature setting button
    if (setTempBtn) {
        setTempBtn.addEventListener('click', function() {
            if (targetTempInput) {
                const newTemp = parseFloat(targetTempInput.value);
                if (!isNaN(newTemp) && newTemp >= 95 && newTemp <= 102) {
                    targetTemperature = newTemp;
                    currentTempTarget.textContent = `${targetTemperature.toFixed(1)} °F`;
                    
                    // Send to server
                    sendSettingUpdate('temperature', targetTemperature);
                    showAlert('warning', `Temperature target set to ${targetTemperature.toFixed(1)} °F`);
                    
                    // Apply auto control if enabled
                    if (autoControlEnabled) {
                        applyAutoControl();
                    }
                } else {
                    showAlert('danger', 'Temperature must be between 95.0°F and 102.0°F');
                }
            }
        });
    }
    
    // Set up humidity setting button
    if (setHumidityBtn) {
        setHumidityBtn.addEventListener('click', function() {
            if (targetHumidityInput) {
                const newHumidity = parseFloat(targetHumidityInput.value);
                if (!isNaN(newHumidity) && newHumidity >= 40 && newHumidity <= 70) {
                    targetHumidity = newHumidity;
                    currentHumidityTarget.textContent = `${targetHumidity.toFixed(0)} %`;
                    
                    // Send to server
                    sendSettingUpdate('humidity', targetHumidity);
                    showAlert('warning', `Humidity target set to ${targetHumidity.toFixed(0)}%`);
                    
                    // Apply auto control if enabled
                    if (autoControlEnabled) {
                        applyAutoControl();
                    }
                } else {
                    showAlert('danger', 'Humidity must be between 40% and 70%');
                }
            }
        });
    }
}

// Setup the auto control toggles
function setupAutoControlToggle() {
    const autoTempToggle = document.getElementById('auto-temp-control-toggle');
    const autoHumidityToggle = document.getElementById('auto-humidity-control-toggle');
    const humidityOverrideToggle = document.getElementById('humidity-override-toggle');
    
    // Try to retrieve auto control states from localStorage
    try {
        const savedAutoTempControl = localStorage.getItem('autoTempControlEnabled');
        if (savedAutoTempControl !== null) {
            autoTempControlEnabled = savedAutoTempControl === 'true';
        }
        
        const savedAutoHumidityControl = localStorage.getItem('autoHumidityControlEnabled');
        if (savedAutoHumidityControl !== null) {
            autoHumidityControlEnabled = savedAutoHumidityControl === 'true';
        }
        
        const savedHumidityOverride = localStorage.getItem('humidityOverride');
        if (savedHumidityOverride !== null) {
            humidityOverride = savedHumidityOverride === 'true';
        }
    } catch (e) {
        console.error('Error accessing localStorage:', e);
    }
    
    // Setup temperature auto control toggle
    if (autoTempToggle) {
        // Set initial state
        autoTempToggle.checked = autoTempControlEnabled;
        
        // Add event listener
        autoTempToggle.addEventListener('change', function() {
            autoTempControlEnabled = this.checked;
            
            // Save to localStorage
            try {
                localStorage.setItem('autoTempControlEnabled', autoTempControlEnabled.toString());
            } catch (e) {
                console.error('Error saving to localStorage:', e);
            }
            
            // Enable/disable manual controls based on auto mode
            updateControlsAvailability();
            
            if (autoTempControlEnabled) {
                showAlert('warning', 'Automatic temperature control activated. Heater controls disabled.');
                // Reset heater1 start time when auto control is enabled
                heater1StartTime = null;
                applyTempControl();
            } else {
                showAlert('warning', 'Manual temperature control activated. You can control heaters manually.');
            }
        });
    }
    
    // Setup humidity auto control toggle
    if (autoHumidityToggle) {
        // Set initial state
        autoHumidityToggle.checked = autoHumidityControlEnabled;
        
        // Add event listener
        autoHumidityToggle.addEventListener('change', function() {
            autoHumidityControlEnabled = this.checked;
            
            // Save to localStorage
            try {
                localStorage.setItem('autoHumidityControlEnabled', autoHumidityControlEnabled.toString());
            } catch (e) {
                console.error('Error saving to localStorage:', e);
            }
            
            if (autoHumidityControlEnabled) {
                if (!humidityOverride) {
                    showAlert('warning', 'Automatic humidity control activated.');
                    applyHumidityControl();
                } else {
                    showAlert('warning', 'Automatic humidity control is on but overridden by humidity override toggle.');
                }
            } else {
                showAlert('warning', 'Manual humidity control activated.');
            }
        });
    }
    
    // Setup humidity override toggle
    if (humidityOverrideToggle) {
        // Set initial state
        humidityOverrideToggle.checked = humidityOverride;
        
        // Add event listener
        humidityOverrideToggle.addEventListener('change', function() {
            humidityOverride = this.checked;
            
            // Save to localStorage
            try {
                localStorage.setItem('humidityOverride', humidityOverride.toString());
            } catch (e) {
                console.error('Error saving to localStorage:', e);
            }
            
            const humidifierToggle = document.getElementById('humidifier-toggle');
            if (humidifierToggle) {
                // Always keep humidifier control enabled regardless of auto mode
                // This is a critical requirement - humidifier can be controlled manually at any time
                humidifierToggle.disabled = false;
                humidifierToggle.parentElement.classList.remove('disabled');
                
                if (humidityOverride) {
                    showAlert('warning', 'Humidity control override activated. Humidity will be controlled manually.');
                } else {
                    showAlert('warning', 'Humidity override deactivated. Auto control will manage humidity, but manual control is still available.');
                }
            }
        });
    }
}

// Update all controls availability based on current states
function updateControlsAvailability() {
    const controlToggles = document.querySelectorAll('.control-toggle');
    const humidifierToggle = document.getElementById('humidifier-toggle');
    
    controlToggles.forEach(toggle => {
        // Always keep humidifier control enabled regardless of auto mode
        if (toggle.id === 'humidifier-toggle') {
            toggle.disabled = false;
            toggle.parentElement.classList.remove('disabled');
        } else {
            // For heaters, follow the auto temperature control logic
            toggle.disabled = autoTempControlEnabled && !overheatingActive;
            if (autoTempControlEnabled && !overheatingActive) {
                toggle.parentElement.classList.add('disabled');
            } else {
                toggle.parentElement.classList.remove('disabled');
            }
        }
    });
}

// Apply temperature control based on current readings and target values
function applyTempControl() {
    if (!autoTempControlEnabled || overheatingActive) return;
    
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            const currentTemp = data.temperature;
            const now = new Date();
            
            // Check for sensor failure - if last reading is more than 2 minutes old
            const lastUpdateTime = data.last_updated * 1000; // Convert to milliseconds
            const currentTime = Date.now();
            
            if (currentTime - lastUpdateTime > 120000) { // 2 minutes in milliseconds
                console.error("SAFETY: Temperature sensor readings are stale, turning off all heaters");
                // Turn off all heaters for safety
                if (data.heater1_on) {
                    sendControlRequest('heater1', 'off');
                }
                if (data.heater2_on) {
                    sendControlRequest('heater2', 'off');
                }
                heater1StartTime = null;
                showAlert('danger', 'Temperature sensor readings are stale. Heaters disabled for safety.');
                return; // Exit function early
            }
            
            // SEQUENTIAL HEATING CONTROL with DYNAMIC thresholds
            // Calculate thresholds based on target temperature (works for any target)
            const turnOnThreshold = targetTemperature - temperatureHysteresis; 
            const turnOffThreshold = targetTemperature;     // Turn off exactly at target
            
            if (currentTemp < turnOnThreshold) {
                // Too cold - apply sequential heating
                if (!data.heater1_on) {
                    // Always turn on heater1 first
                    sendControlRequest('heater1', 'on');
                    // Record when heater1 was turned on
                    heater1StartTime = now;
                } else if (!data.heater2_on) {
                    // If heater1 is already on, check if we should turn on heater2
                    if (heater1StartTime) {
                        const timeSinceHeater1Start = (now - heater1StartTime) / 1000; // in seconds
                        // Turn on heater2 if heater1 has been running for 3+ minutes and we're still too cold
                        if (timeSinceHeater1Start >= 180) { // 3 minutes = 180 seconds
                            sendControlRequest('heater2', 'on');
                        }
                    }
                }
            } else if (currentTemp >= turnOffThreshold) {
                // At or above target - turn off heaters in reverse order (heater2 first)
                if (data.heater2_on) {
                    sendControlRequest('heater2', 'off');
                } else if (data.heater1_on) {
                    sendControlRequest('heater1', 'off');
                    heater1StartTime = null; // Reset the heater1 start time
                }
            }
        })
        .catch(error => {
            console.error('Error in temperature control:', error);
        });
}

// Apply humidity control based on current readings and target values
function applyHumidityControl() {
    if (!autoHumidityControlEnabled || humidityOverride) return;
    
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            const currentHumidity = data.humidity;
            
            // Check for sensor failure - if last reading is more than 2 minutes old
            const lastUpdateTime = data.last_updated * 1000; // Convert to milliseconds
            const currentTime = Date.now();
            
            if (currentTime - lastUpdateTime > 120000) { // 2 minutes in milliseconds
                console.error("SAFETY: Humidity sensor readings are stale, turning off humidifier");
                // Turn off humidifier for safety
                if (data.humidifier_on) {
                    sendControlRequest('humidifier', 'off');
                }
                showAlert('danger', 'Humidity sensor readings are stale. Humidifier disabled for safety.');
                return; // Exit function early
            }
            
            // Control humidity with hysteresis
            if (currentHumidity < targetHumidity - 3) {
                // Too dry, turn on humidifier
                if (!data.humidifier_on) sendControlRequest('humidifier', 'on');
            } else if (currentHumidity > targetHumidity + 3) {
                // Too humid, turn off humidifier
                if (data.humidifier_on) sendControlRequest('humidifier', 'off');
            }
        })
        .catch(error => {
            console.error('Error in humidity control:', error);
        });
}

// Legacy function to maintain compatibility
function applyAutoControl() {
    if (autoTempControlEnabled) {
        applyTempControl();
    }
    
    if (autoHumidityControlEnabled && !humidityOverride) {
        applyHumidityControl();
    }
}

// Send a setting update to the server
function sendSettingUpdate(setting, value) {
    fetch('/api/settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            setting: setting,
            value: value
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Setting update response:', data);
    })
    .catch(error => {
        console.error('Error updating setting:', error);
    });
}

// Add auto control to the status update function
const originalUpdateStatus = updateStatus;
updateStatus = function() {
    originalUpdateStatus();
    
    // Apply auto control on each status update
    if (autoTempControlEnabled) {
        setTimeout(applyTempControl, 1000); // Slight delay to ensure latest data
    }
    
    if (autoHumidityControlEnabled && !humidityOverride) {
        setTimeout(applyHumidityControl, 1000);
    }
};

// Cleanup function to execute when page is unloaded
window.addEventListener('beforeunload', function() {
    // Clear the update interval
    if (updateInterval) {
        clearInterval(updateInterval);
    }
});
