"""FastAPI server for eonapi web UI."""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .api import EonNextAPI


app = FastAPI(title="eonapi Web UI")


class LoginRequest(BaseModel):
    """Request model for login."""
    username: str
    password: str
    days: int = 30
    meter_serial: Optional[str] = None


class MeterData(BaseModel):
    """Response model for meter data."""
    meter_serial: str
    meter_type: str
    start_date: str
    end_date: str
    total_kwh: float
    avg_daily: float
    peak_kwh: float
    peak_time: str
    consumption_data: list[dict]


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the web UI."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>E.ON API - Energy Consumption Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/vue@3/dist/vue.global.prod.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/apexcharts@3.44.0/dist/apexcharts.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <div id="app" class="min-h-screen">
        <!-- Header -->
        <header class="bg-blue-600 text-white shadow-lg">
            <div class="container mx-auto px-4 py-6">
                <h1 class="text-3xl font-bold">⚡ E.ON API Dashboard</h1>
                <p class="text-blue-100 mt-2">Energy Consumption Analysis</p>
            </div>
        </header>

        <!-- Main Content -->
        <main class="container mx-auto px-4 py-8">
            <!-- Login Form -->
            <div v-if="!isAuthenticated" class="max-w-md mx-auto">
                <div class="bg-white rounded-lg shadow-md p-6">
                    <h2 class="text-2xl font-bold mb-6 text-gray-800">Login to E.ON Next</h2>

                    <form @submit.prevent="handleLogin">
                        <div class="mb-4">
                            <label class="block text-gray-700 font-medium mb-2">Username (Email)</label>
                            <input
                                v-model="credentials.username"
                                type="email"
                                required
                                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="your@email.com"
                            />
                        </div>

                        <div class="mb-4">
                            <label class="block text-gray-700 font-medium mb-2">Password</label>
                            <input
                                v-model="credentials.password"
                                type="password"
                                required
                                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="••••••••"
                            />
                        </div>

                        <div class="mb-6">
                            <label class="block text-gray-700 font-medium mb-2">Days to Retrieve</label>
                            <input
                                v-model.number="credentials.days"
                                type="number"
                                min="1"
                                max="365"
                                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        </div>

                        <button
                            type="submit"
                            :disabled="loading"
                            class="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition duration-200"
                        >
                            <span v-if="loading">Loading...</span>
                            <span v-else>Fetch Data</span>
                        </button>
                    </form>

                    <div v-if="error" class="mt-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                        {{ error }}
                    </div>

                    <div class="mt-4 bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded text-sm">
                        <p class="font-semibold">🔒 Privacy Note</p>
                        <p class="mt-1">Credentials and data are stored locally in your browser to avoid re-login on refresh. Click Logout to clear.</p>
                    </div>
                </div>
            </div>

            <!-- Dashboard -->
            <div v-else>
                <!-- Stats Cards -->
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                    <div class="bg-white rounded-lg shadow-md p-6">
                        <h3 class="text-gray-500 text-sm font-medium">Total Consumption</h3>
                        <p class="text-3xl font-bold text-blue-600 mt-2">{{ meterData.total_kwh.toFixed(2) }}</p>
                        <p class="text-gray-600 text-sm mt-1">kWh</p>
                    </div>

                    <div class="bg-white rounded-lg shadow-md p-6">
                        <h3 class="text-gray-500 text-sm font-medium">Average Daily</h3>
                        <p class="text-3xl font-bold text-green-600 mt-2">{{ meterData.avg_daily.toFixed(2) }}</p>
                        <p class="text-gray-600 text-sm mt-1">kWh/day</p>
                    </div>

                    <div class="bg-white rounded-lg shadow-md p-6">
                        <h3 class="text-gray-500 text-sm font-medium">Peak Usage</h3>
                        <p class="text-3xl font-bold text-orange-600 mt-2">{{ meterData.peak_kwh.toFixed(2) }}</p>
                        <p class="text-gray-600 text-sm mt-1">kWh</p>
                    </div>

                    <div class="bg-white rounded-lg shadow-md p-6">
                        <h3 class="text-gray-500 text-sm font-medium">Meter Type</h3>
                        <p class="text-2xl font-bold text-purple-600 mt-2 capitalize">{{ meterData.meter_type }}</p>
                        <p class="text-gray-600 text-sm mt-1">{{ meterData.meter_serial }}</p>
                    </div>
                </div>

                <!-- Chart -->
                <div class="bg-white rounded-lg shadow-md p-6 mb-8">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-xl font-bold text-gray-800">
                            <span v-if="!selectedDay">Daily Consumption</span>
                            <span v-else>Half-hourly Consumption - {{ selectedDay }}</span>
                        </h3>
                        <button
                            v-if="selectedDay"
                            @click="backToDaily"
                            class="bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition duration-200 text-sm"
                        >
                            ← Back to Daily View
                        </button>
                    </div>
                    <p v-if="!selectedDay" class="text-gray-600 text-sm mb-4">Click on a bar to see half-hourly breakdown</p>
                    <div id="mainChart"></div>
                </div>

                <!-- Peak Time Info -->
                <div class="bg-white rounded-lg shadow-md p-6 mb-8">
                    <h3 class="text-xl font-bold text-gray-800 mb-4">Peak Usage Details</h3>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                            <p class="text-gray-600">Peak Time</p>
                            <p class="font-semibold text-lg">{{ formatDateTime(meterData.peak_time) }}</p>
                        </div>
                        <div>
                            <p class="text-gray-600">Date Range</p>
                            <p class="font-semibold text-lg">{{ formatDate(meterData.start_date) }} - {{ formatDate(meterData.end_date) }}</p>
                        </div>
                        <div>
                            <p class="text-gray-600">Total Intervals</p>
                            <p class="font-semibold text-lg">{{ meterData.consumption_data.length }}</p>
                        </div>
                    </div>
                </div>

                <!-- Actions -->
                <div class="text-center space-x-4">
                    <button
                        @click="refreshData"
                        class="bg-blue-600 text-white py-2 px-6 rounded-lg hover:bg-blue-700 transition duration-200"
                        :disabled="loading"
                    >
                        <span v-if="loading">Refreshing...</span>
                        <span v-else">Refresh Data</span>
                    </button>
                    <button
                        @click="logout"
                        class="bg-gray-600 text-white py-2 px-6 rounded-lg hover:bg-gray-700 transition duration-200"
                    >
                        Logout
                    </button>
                </div>
            </div>
        </main>

        <!-- Footer -->
        <footer class="bg-gray-800 text-white mt-12">
            <div class="container mx-auto px-4 py-6 text-center">
                <p class="text-sm">E.ON API - Energy Consumption Dashboard</p>
                <p class="text-xs text-gray-400 mt-2">Unofficial tool - Not affiliated with E.ON Next</p>
            </div>
        </footer>
    </div>

    <script>
        const { createApp } = Vue;

        createApp({
            data() {
                return {
                    credentials: {
                        username: '',
                        password: '',
                        days: 30
                    },
                    isAuthenticated: false,
                    loading: false,
                    error: null,
                    meterData: null,
                    mainChart: null,
                    selectedDay: null,
                    dailyDataMap: {}
                };
            },
            async mounted() {
                // Log version for debugging
                console.log('%c🔌 E.ON API UI v0.2.0', 'color: #3b82f6; font-weight: bold; font-size: 14px;');
                console.log('Build: 2025-11-13 | ApexCharts with 200ms animations');

                // Check if we have cached data
                const cachedData = localStorage.getItem('eonapi_meter_data');
                const cachedCredentials = localStorage.getItem('eonapi_credentials');

                if (cachedData && cachedCredentials) {
                    try {
                        this.meterData = JSON.parse(cachedData);
                        this.credentials = JSON.parse(cachedCredentials);
                        this.isAuthenticated = true;

                        await this.$nextTick();
                        await this.createCharts();
                    } catch (e) {
                        // If parsing fails, clear cache
                        localStorage.removeItem('eonapi_meter_data');
                        localStorage.removeItem('eonapi_credentials');
                    }
                }
            },
            methods: {
                async handleLogin() {
                    this.loading = true;
                    this.error = null;

                    try {
                        const response = await fetch('/api/meter-data', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify(this.credentials)
                        });

                        if (!response.ok) {
                            const error = await response.json();
                            throw new Error(error.detail || 'Failed to fetch data');
                        }

                        this.meterData = await response.json();
                        this.isAuthenticated = true;

                        // Save to localStorage
                        localStorage.setItem('eonapi_meter_data', JSON.stringify(this.meterData));
                        localStorage.setItem('eonapi_credentials', JSON.stringify(this.credentials));

                        // Wait for DOM update before creating charts
                        await this.$nextTick();
                        await this.createCharts();
                    } catch (err) {
                        this.error = err.message;
                    } finally {
                        this.loading = false;
                    }
                },

                async refreshData() {
                    // Re-fetch data using stored credentials
                    await this.handleLogin();
                },

                logout() {
                    // Destroy chart first
                    if (this.mainChart) {
                        this.mainChart.destroy();
                        this.mainChart = null;
                    }

                    this.isAuthenticated = false;
                    this.meterData = null;
                    this.credentials.password = '';
                    this.selectedDay = null;

                    // Clear localStorage
                    localStorage.removeItem('eonapi_meter_data');
                    localStorage.removeItem('eonapi_credentials');
                },

                formatDate(dateStr) {
                    return new Date(dateStr).toLocaleDateString();
                },

                formatDateTime(dateStr) {
                    return new Date(dateStr).toLocaleString();
                },

                async createCharts() {
                    // Prepare data for daily aggregation
                    this.dailyDataMap = {};
                    this.meterData.consumption_data.forEach(d => {
                        const date = new Date(d.startAt).toLocaleDateString();
                        if (!this.dailyDataMap[date]) {
                            this.dailyDataMap[date] = {
                                total: 0,
                                intervals: []
                            };
                        }
                        this.dailyDataMap[date].total += parseFloat(d.value);
                        this.dailyDataMap[date].intervals.push(d);
                    });

                    await this.createDailyChart();
                },

                async createDailyChart() {
                    // Destroy existing chart if any
                    if (this.mainChart) {
                        this.mainChart.destroy();
                        this.mainChart = null;
                    }

                    const dates = Object.keys(this.dailyDataMap);
                    const values = Object.values(this.dailyDataMap).map(d => d.total.toFixed(2));

                    const options = {
                        series: [{
                            name: 'Daily Consumption',
                            data: values
                        }],
                        chart: {
                            type: 'bar',
                            height: 400,
                            animations: {
                                enabled: true,
                                speed: 200,
                                animateGradually: {
                                    enabled: false
                                }
                            },
                            events: {
                                dataPointSelection: (event, chartContext, config) => {
                                    const selectedDate = dates[config.dataPointIndex];
                                    this.showDayDetails(selectedDate);
                                }
                            },
                            toolbar: {
                                show: false
                            }
                        },
                        plotOptions: {
                            bar: {
                                borderRadius: 4,
                                dataLabels: {
                                    position: 'top'
                                }
                            }
                        },
                        dataLabels: {
                            enabled: false
                        },
                        xaxis: {
                            categories: dates,
                            labels: {
                                rotate: -45,
                                rotateAlways: true
                            }
                        },
                        yaxis: {
                            title: {
                                text: 'Consumption (kWh)'
                            },
                            labels: {
                                formatter: (val) => val.toFixed(2)
                            }
                        },
                        tooltip: {
                            y: {
                                formatter: (val) => `${parseFloat(val).toFixed(2)} kWh`
                            }
                        },
                        colors: ['#22c55e'],
                        fill: {
                            opacity: 0.8
                        }
                    };

                    this.mainChart = new ApexCharts(document.querySelector("#mainChart"), options);
                    await this.mainChart.render();
                },

                async showDayDetails(date) {
                    const dayData = this.dailyDataMap[date];

                    if (!dayData || !dayData.intervals || dayData.intervals.length === 0) {
                        console.error('No data available for date:', date);
                        return;
                    }

                    // Sort intervals by time
                    const sortedIntervals = dayData.intervals.sort((a, b) => {
                        return new Date(a.startAt) - new Date(b.startAt);
                    });

                    const labels = sortedIntervals.map(d => {
                        const date = new Date(d.startAt);
                        return date.toLocaleTimeString('en-GB', {
                            hour: '2-digit',
                            minute: '2-digit'
                        });
                    });
                    const values = sortedIntervals.map(d => parseFloat(d.value).toFixed(3));

                    // Update selected day
                    this.selectedDay = date;

                    // Destroy and recreate chart
                    if (this.mainChart) {
                        this.mainChart.destroy();
                        this.mainChart = null;
                    }

                    await this.$nextTick();

                    const options = {
                        series: [{
                            name: 'Half-hourly Consumption',
                            data: values
                        }],
                        chart: {
                            type: 'bar',
                            height: 400,
                            animations: {
                                enabled: true,
                                speed: 200,
                                animateGradually: {
                                    enabled: false
                                }
                            },
                            toolbar: {
                                show: false
                            }
                        },
                        plotOptions: {
                            bar: {
                                borderRadius: 4,
                                dataLabels: {
                                    position: 'top'
                                }
                            }
                        },
                        dataLabels: {
                            enabled: false
                        },
                        xaxis: {
                            categories: labels,
                            labels: {
                                rotate: -45,
                                rotateAlways: true
                            }
                        },
                        yaxis: {
                            title: {
                                text: 'Consumption (kWh)'
                            },
                            labels: {
                                formatter: (val) => parseFloat(val).toFixed(3)
                            }
                        },
                        tooltip: {
                            y: {
                                formatter: (val) => `${parseFloat(val).toFixed(3)} kWh`
                            }
                        },
                        colors: ['#3b82f6'],
                        fill: {
                            opacity: 0.8
                        }
                    };

                    this.mainChart = new ApexCharts(document.querySelector("#mainChart"), options);
                    await this.mainChart.render();
                },

                async backToDaily() {
                    this.selectedDay = null;
                    await this.createDailyChart();
                }
            }
        }).mount('#app');
    </script>
</body>
</html>
    """


@app.post("/api/meter-data", response_model=MeterData)
async def get_meter_data(request: LoginRequest):
    """Fetch meter data using provided credentials."""
    try:
        api = EonNextAPI()

        # Authenticate
        if not await api.login(request.username, request.password):
            raise HTTPException(status_code=401, detail="Authentication failed")

        # Get accounts
        accounts = await api.get_account_numbers()
        if not accounts:
            raise HTTPException(status_code=404, detail="No accounts found")

        account_number = accounts[0]

        # Get meters
        meters = await api.get_meters(account_number)
        if not meters:
            raise HTTPException(status_code=404, detail="No meters found")

        # Select meter
        selected_meter = None
        if request.meter_serial:
            for meter in meters:
                if meter["serial"] == request.meter_serial:
                    selected_meter = meter
                    break
            if not selected_meter:
                raise HTTPException(
                    status_code=404,
                    detail=f"Meter with serial {request.meter_serial} not found"
                )
        else:
            selected_meter = meters[0]

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=request.days)

        # Fetch consumption data
        consumption = await api.get_consumption_data(
            account_number=account_number,
            meter_id=selected_meter["id"],
            meter_type=selected_meter["type"],
            start_date=start_date,
            end_date=end_date,
            progress_callback=None
        )

        if not consumption:
            raise HTTPException(status_code=404, detail="No consumption data available")

        # Calculate statistics
        total_kwh = sum(float(record.get("value", 0)) for record in consumption)
        num_days = len(consumption) / 48
        avg_daily = total_kwh / num_days if num_days > 0 else 0

        peak_record = max(consumption, key=lambda r: float(r.get("value", 0)))
        peak_kwh = float(peak_record.get("value", 0))
        peak_time = peak_record.get("startAt", "")

        return MeterData(
            meter_serial=selected_meter["serial"],
            meter_type=selected_meter["type"],
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            total_kwh=total_kwh,
            avg_daily=avg_daily,
            peak_kwh=peak_kwh,
            peak_time=peak_time,
            consumption_data=consumption
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
