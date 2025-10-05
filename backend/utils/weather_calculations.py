import numpy as np
from datetime import datetime, date, timedelta
from typing import List, Tuple, Optional
import math


def calculate_growing_degree_days(
    temp_max: float, 
    temp_min: float, 
    base_temp: float = 10.0
) -> float:
    """Calculate growing degree days for a given day"""
    
    avg_temp = (temp_max + temp_min) / 2
    return max(0, avg_temp - base_temp)


def calculate_heat_index(temperature: float, humidity: float) -> float:
    """Calculate heat index (apparent temperature)"""
    
    if temperature < 27:  # Heat index only relevant for high temps
        return temperature
    
    # Convert to Fahrenheit for calculation
    temp_f = temperature * 9/5 + 32
    
    # Rothfusz regression equation
    hi = (
        -42.379 +
        2.04901523 * temp_f +
        10.14333127 * humidity +
        -0.22475541 * temp_f * humidity +
        -0.00683783 * temp_f * temp_f +
        -0.05481717 * humidity * humidity +
        0.00122874 * temp_f * temp_f * humidity +
        0.00085282 * temp_f * humidity * humidity +
        -0.00000199 * temp_f * temp_f * humidity * humidity
    )
    
    # Convert back to Celsius
    return (hi - 32) * 5/9


def calculate_wind_chill(temperature: float, wind_speed_kmh: float) -> float:
    """Calculate wind chill temperature"""
    
    if temperature > 10 or wind_speed_kmh < 4.8:  # Wind chill only for cold, windy conditions
        return temperature
    
    # Environment Canada wind chill formula
    wind_chill = (
        13.12 +
        0.6215 * temperature -
        11.37 * (wind_speed_kmh ** 0.16) +
        0.3965 * temperature * (wind_speed_kmh ** 0.16)
    )
    
    return wind_chill


def calculate_dewpoint(temperature: float, humidity: float) -> float:
    """Calculate dewpoint temperature"""
    
    # Magnus formula approximation
    a = 17.27
    b = 237.7
    
    alpha = ((a * temperature) / (b + temperature)) + math.log(humidity / 100.0)
    dewpoint = (b * alpha) / (a - alpha)
    
    return dewpoint


def calculate_vapor_pressure_deficit(temperature: float, humidity: float) -> float:
    """Calculate vapor pressure deficit (VPD)"""
    
    # Saturation vapor pressure (kPa)
    svp = 0.6108 * math.exp((17.27 * temperature) / (temperature + 237.3))
    
    # Actual vapor pressure
    avp = svp * (humidity / 100.0)
    
    # Vapor pressure deficit
    vpd = svp - avp
    
    return vpd


def classify_precipitation_intensity(precip_mm: float) -> str:
    """Classify precipitation intensity"""
    
    if precip_mm < 0.1:
        return "no_precipitation"
    elif precip_mm < 2.5:
        return "light"
    elif precip_mm < 10.0:
        return "moderate"
    elif precip_mm < 50.0:
        return "heavy"
    else:
        return "extreme"


def calculate_potential_evapotranspiration(
    temperature: float, 
    humidity: float, 
    wind_speed: float,
    day_of_year: int,
    latitude: float
) -> float:
    """Calculate potential evapotranspiration using Penman-Monteith approximation"""
    
    # Simplified Penman-Monteith equation
    # This is a basic approximation - full calculation requires solar radiation data
    
    # Saturation vapor pressure
    svp = 0.6108 * math.exp((17.27 * temperature) / (temperature + 237.3))
    
    # Slope of saturation vapor pressure curve
    delta = (4098 * svp) / ((temperature + 237.3) ** 2)
    
    # Psychrometric constant
    gamma = 0.665  # kPa/°C (approximate for sea level)
    
    # Net radiation (simplified approximation)
    solar_declination = 23.45 * math.sin(math.radians(360 * (284 + day_of_year) / 365))
    hour_angle = math.acos(-math.tan(math.radians(latitude)) * math.tan(math.radians(solar_declination)))
    
    # Simplified net radiation calculation
    rn = max(0, 15 * (temperature + 5))  # Very simplified approximation
    
    # Aerodynamic term
    u2 = wind_speed * 4.87 / math.log(67.8 * 10 - 5.42)  # Convert to 2m height
    aerodynamic = (900 / (temperature + 273)) * u2 * (svp - svp * humidity / 100)
    
    # PET calculation
    pet = (delta * rn + gamma * aerodynamic) / (delta + gamma * (1 + 0.34 * u2))
    
    return max(0, pet)


def calculate_comfort_index(temperature: float, humidity: float, wind_speed: float) -> Tuple[float, str]:
    """Calculate human comfort index and classification"""
    
    # Calculate apparent temperature
    if temperature > 27:
        apparent_temp = calculate_heat_index(temperature, humidity)
    elif temperature < 10 and wind_speed > 4.8:
        apparent_temp = calculate_wind_chill(temperature, wind_speed * 3.6)  # Convert m/s to km/h
    else:
        apparent_temp = temperature
    
    # Comfort classification
    if apparent_temp < -10:
        comfort = "extremely_cold"
    elif apparent_temp < 0:
        comfort = "very_cold"
    elif apparent_temp < 10:
        comfort = "cold"
    elif apparent_temp < 18:
        comfort = "cool"
    elif apparent_temp < 24:
        comfort = "comfortable"
    elif apparent_temp < 30:
        comfort = "warm"
    elif apparent_temp < 35:
        comfort = "hot"
    else:
        comfort = "extremely_hot"
    
    return apparent_temp, comfort


def interpolate_missing_values(values: List[float], max_gap: int = 3) -> List[float]:
    """Interpolate missing values in a time series"""
    
    result = values.copy()
    n = len(values)
    
    for i in range(n):
        if math.isnan(result[i]):
            # Find nearest valid values
            left_val, left_idx = None, None
            right_val, right_idx = None, None
            
            # Search left
            for j in range(i - 1, max(0, i - max_gap - 1), -1):
                if not math.isnan(result[j]):
                    left_val, left_idx = result[j], j
                    break
            
            # Search right
            for j in range(i + 1, min(n, i + max_gap + 1)):
                if not math.isnan(result[j]):
                    right_val, right_idx = result[j], j
                    break
            
            # Interpolate
            if left_val is not None and right_val is not None:
                # Linear interpolation
                weight = (i - left_idx) / (right_idx - left_idx)
                result[i] = left_val + weight * (right_val - left_val)
            elif left_val is not None:
                result[i] = left_val
            elif right_val is not None:
                result[i] = right_val
    
    return result


def calculate_seasonal_amplitude(monthly_values: List[float]) -> float:
    """Calculate seasonal amplitude (max - min) from monthly values"""
    
    if len(monthly_values) != 12:
        raise ValueError("Monthly values must contain exactly 12 values")
    
    return max(monthly_values) - min(monthly_values)


def smooth_time_series(values: List[float], window_size: int = 7) -> List[float]:
    """Apply moving average smoothing to time series"""
    
    if window_size < 1:
        return values
    
    smoothed = []
    half_window = window_size // 2
    
    for i in range(len(values)):
        start_idx = max(0, i - half_window)
        end_idx = min(len(values), i + half_window + 1)
        
        window_values = [v for v in values[start_idx:end_idx] if not math.isnan(v)]
        
        if window_values:
            smoothed.append(sum(window_values) / len(window_values))
        else:
            smoothed.append(values[i])
    
    return smoothed


def detect_outliers(values: List[float], threshold: float = 3.0) -> List[bool]:
    """Detect outliers using modified z-score method"""
    
    # Calculate median and median absolute deviation
    sorted_values = sorted([v for v in values if not math.isnan(v)])
    n = len(sorted_values)
    
    if n < 3:
        return [False] * len(values)
    
    median = sorted_values[n // 2]
    mad = np.median([abs(v - median) for v in sorted_values])
    
    if mad == 0:
        return [False] * len(values)
    
    # Calculate modified z-scores
    outliers = []
    for value in values:
        if math.isnan(value):
            outliers.append(False)
        else:
            modified_z_score = 0.6745 * (value - median) / mad
            outliers.append(abs(modified_z_score) > threshold)
    
    return outliers