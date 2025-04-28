// JavaScript for analytics page
let temperatureChart, humidityChart, relayStateChart;

// Chart colors
const chartColors = {
    temperature: '#ff6b6b',
    humidity: '#4dabf7',
    heater1: '#ffa94d',
    heater2: '#ff8c42',
    humidifier: '#63e6be',
    grid: '#636990',
    text: '#c7c8d9'
};

// Initialize page on document ready
document.addEventListener('DOMContentLoaded', function() {
    initCharts();
    
    // Set up event listeners for time range and interval selectors
    document.getElementById('time-range').addEventListener('change', fetchAndUpdateCharts);
    document.getElementById('interval').addEventListener('change', fetchAndUpdateCharts);
    
    // Initial data fetch
    fetchAndUpdateCharts();
    
    // Set up auto-refresh every 5 minutes
    setInterval(fetchAndUpdateCharts, 5 * 60 * 1000);
});

// Initialize Charts with Chart.js
function initCharts() {
    // Common options for all charts
    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
            duration: 500
        },
        plugins: {
            legend: {
                labels: {
                    color: chartColors.text,
                    font: {
                        family: "'Arial', sans-serif",
                        size: 12
                    }
                }
            },
            tooltip: {
                mode: 'index',
                intersect: false,
                titleFont: {
                    size: 14,
                    weight: 'bold'
                },
                bodyFont: {
                    size: 13
                },
                padding: 10,
                backgroundColor: 'rgba(20, 20, 30, 0.9)',
                titleColor: '#ffffff',
                bodyColor: '#e2e2e2',
                borderColor: '#444',
                borderWidth: 1
            }
        },
        scales: {
            x: {
                type: 'time',
                time: {
                    tooltipFormat: 'MMM d, HH:mm',
                    displayFormats: {
                        hour: 'HH:mm',
                        minute: 'HH:mm'
                    }
                },
                grid: {
                    color: chartColors.grid,
                    borderColor: chartColors.grid,
                    tickColor: chartColors.grid
                },
                ticks: {
                    color: chartColors.text,
                    maxRotation: 0,
                    autoSkip: true,
                    maxTicksLimit: 10
                }
            },
            y: {
                beginAtZero: false,
                grid: {
                    color: chartColors.grid,
                    borderColor: chartColors.grid,
                    tickColor: chartColors.grid
                },
                ticks: {
                    color: chartColors.text
                }
            }
        }
    };
    
    // Temperature Chart
    const temperatureCtx = document.getElementById('temperature-chart').getContext('2d');
    temperatureChart = new Chart(temperatureCtx, {
        type: 'line',
        data: {
            datasets: [{
                label: 'Temperature (°F)',
                data: [],
                borderColor: chartColors.temperature,
                backgroundColor: 'rgba(255, 107, 107, 0.1)',
                borderWidth: 2,
                pointRadius: 1,
                pointHoverRadius: 5,
                tension: 0.3,
                fill: true
            }, {
                label: 'Target Temperature',
                data: [],
                borderColor: 'rgba(255, 255, 255, 0.5)',
                borderWidth: 1,
                borderDash: [5, 5],
                pointRadius: 0,
                fill: false
            }]
        },
        options: {
            ...commonOptions,
            interaction: {
                mode: 'index',
                intersect: false
            }
        }
    });
    
    // Humidity Chart
    const humidityCtx = document.getElementById('humidity-chart').getContext('2d');
    humidityChart = new Chart(humidityCtx, {
        type: 'line',
        data: {
            datasets: [{
                label: 'Humidity (%)',
                data: [],
                borderColor: chartColors.humidity,
                backgroundColor: 'rgba(77, 171, 247, 0.1)',
                borderWidth: 2,
                pointRadius: 1,
                pointHoverRadius: 5,
                tension: 0.3,
                fill: true
            }, {
                label: 'Target Humidity',
                data: [],
                borderColor: 'rgba(255, 255, 255, 0.5)',
                borderWidth: 1,
                borderDash: [5, 5],
                pointRadius: 0,
                fill: false
            }]
        },
        options: {
            ...commonOptions,
            interaction: {
                mode: 'index',
                intersect: false
            }
        }
    });
    
    // Relay States Chart
    const relayStateCtx = document.getElementById('relay-states-chart').getContext('2d');
    relayStateChart = new Chart(relayStateCtx, {
        type: 'line',
        data: {
            datasets: [{
                label: 'Heater 1',
                data: [],
                borderColor: chartColors.heater1,
                backgroundColor: 'rgba(255, 169, 77, 0.1)',
                borderWidth: 2,
                pointRadius: 0,
                steppedLine: true,
                fill: true,
                tension: 0
            }, {
                label: 'Heater 2',
                data: [],
                borderColor: chartColors.heater2,
                backgroundColor: 'rgba(255, 140, 66, 0.1)',
                borderWidth: 2,
                pointRadius: 0,
                steppedLine: true,
                fill: true,
                tension: 0
            }, {
                label: 'Humidifier',
                data: [],
                borderColor: chartColors.humidifier,
                backgroundColor: 'rgba(99, 230, 190, 0.1)',
                borderWidth: 2,
                pointRadius: 0,
                steppedLine: true,
                fill: true,
                tension: 0
            }]
        },
        options: {
            ...commonOptions,
            scales: {
                ...commonOptions.scales,
                y: {
                    min: -0.1,
                    max: 1.1,
                    grid: {
                        color: chartColors.grid,
                        borderColor: chartColors.grid,
                        tickColor: chartColors.grid
                    },
                    ticks: {
                        color: chartColors.text,
                        callback: function(value) {
                            if (value === 0) return 'OFF';
                            if (value === 1) return 'ON';
                            return '';
                        }
                    }
                }
            }
        }
    });
}

// Fetch data from API and update charts
function fetchAndUpdateCharts() {
    const timeRange = document.getElementById('time-range').value;
    const interval = document.getElementById('interval').value;
    
    // Show loading indicator
    document.querySelectorAll('.chart-loading').forEach(el => {
        el.style.display = 'flex';
    });
    
    fetch(`/api/analytics?days=${timeRange}&interval=${interval}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Update charts with the fetched data
            updateCharts(data);
            
            // Update statistics
            updateStatistics(data);
            
            // Hide loading indicators
            document.querySelectorAll('.chart-loading').forEach(el => {
                el.style.display = 'none';
            });
        })
        .catch(error => {
            console.error('Error fetching analytics data:', error);
            showError('Failed to load analytics data. Please try again later.');
            
            // Hide loading indicators
            document.querySelectorAll('.chart-loading').forEach(el => {
                el.style.display = 'none';
            });
        });
}

// Update charts with data
function updateCharts(data) {
    if (!data || !data.timestamp || data.timestamp.length === 0) {
        showError('No data available for the selected time range.');
        return;
    }
    
    // Format the data for Chart.js
    const chartData = [];
    for (let i = 0; i < data.timestamp.length; i++) {
        const timestamp = new Date(data.timestamp[i] * 1000);
        
        // Temperature data point
        chartData.push({
            timestamp,
            temperature: data.temperature[i],
            humidity: data.humidity[i],
            heater1: data.heater1_on[i] ? 1 : 0,
            heater2: data.heater2_on[i] ? 1 : 0,
            humidifier: data.humidifier_on[i] ? 1 : 0,
            target_temperature: data.target_temperature[i],
            target_humidity: data.target_humidity[i]
        });
    }
    
    // Update temperature chart
    temperatureChart.data.datasets[0].data = chartData.map(point => ({
        x: point.timestamp,
        y: point.temperature
    }));
    
    // Add target temperature line
    temperatureChart.data.datasets[1].data = chartData.map(point => ({
        x: point.timestamp,
        y: point.target_temperature
    }));
    
    // Update humidity chart
    humidityChart.data.datasets[0].data = chartData.map(point => ({
        x: point.timestamp,
        y: point.humidity
    }));
    
    // Add target humidity line
    humidityChart.data.datasets[1].data = chartData.map(point => ({
        x: point.timestamp,
        y: point.target_humidity
    }));
    
    // Update relay states chart
    relayStateChart.data.datasets[0].data = chartData.map(point => ({
        x: point.timestamp,
        y: point.heater1
    }));
    
    relayStateChart.data.datasets[1].data = chartData.map(point => ({
        x: point.timestamp,
        y: point.heater2
    }));
    
    relayStateChart.data.datasets[2].data = chartData.map(point => ({
        x: point.timestamp,
        y: point.humidifier
    }));
    
    // Update all charts
    temperatureChart.update();
    humidityChart.update();
    relayStateChart.update();
}

// Update statistics section
function updateStatistics(data) {
    if (!data || !data.temperature || data.temperature.length === 0) {
        return;
    }
    
    // Calculate statistics
    const avgTemp = calculateAverage(data.temperature).toFixed(1);
    const avgHumidity = calculateAverage(data.humidity).toFixed(1);
    const minTemp = Math.min(...data.temperature).toFixed(1);
    const maxTemp = Math.max(...data.temperature).toFixed(1);
    const minHumidity = Math.min(...data.humidity).toFixed(1);
    const maxHumidity = Math.max(...data.humidity).toFixed(1);
    
    // Calculate duty cycles (percentage of time ON)
    const heater1DutyCycle = calculateDutyCycle(data.heater1_on).toFixed(1);
    const heater2DutyCycle = calculateDutyCycle(data.heater2_on).toFixed(1);
    const humidifierDutyCycle = calculateDutyCycle(data.humidifier_on).toFixed(1);
    
    // Update the DOM
    document.getElementById('avg-temp').textContent = `${avgTemp}°F`;
    document.getElementById('min-temp').textContent = `${minTemp}°F`;
    document.getElementById('max-temp').textContent = `${maxTemp}°F`;
    document.getElementById('avg-humidity').textContent = `${avgHumidity}%`;
    document.getElementById('min-humidity').textContent = `${minHumidity}%`;
    document.getElementById('max-humidity').textContent = `${maxHumidity}%`;
    document.getElementById('heater1-duty').textContent = `${heater1DutyCycle}%`;
    document.getElementById('heater2-duty').textContent = `${heater2DutyCycle}%`;
    document.getElementById('humidifier-duty').textContent = `${humidifierDutyCycle}%`;
}

// Helper function to calculate average of array values
function calculateAverage(values) {
    if (!values || values.length === 0) return 0;
    const sum = values.reduce((a, b) => a + b, 0);
    return sum / values.length;
}

// Helper function to calculate duty cycle (percentage of time ON)
function calculateDutyCycle(states) {
    if (!states || states.length === 0) return 0;
    const onCount = states.filter(state => state).length;
    return (onCount / states.length) * 100;
}

// Display error message
function showError(message) {
    const errorElement = document.getElementById('error-message');
    errorElement.textContent = message;
    errorElement.style.display = 'block';
    
    // Hide after 5 seconds
    setTimeout(() => {
        errorElement.style.display = 'none';
    }, 5000);
}