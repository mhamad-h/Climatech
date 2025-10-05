import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple, Optional, Any
from scipy import stats
from scipy.interpolate import interp1d
import math

from models.weather_data import (
    HistoricalWeatherData, WeatherForecast, ClimateNormal, 
    WeatherCondition, WindDirection, ConfidenceLevel
)


class ClimatologyService:
    """Service for climatological calculations and analysis"""
    
    def __init__(self):
        self.DAYS_IN_YEAR = 365
        self.CLIMATOLOGY_WINDOW = 30  # Days for rolling average
    
    def calculate_day_of_year_climatology(
        self, 
        historical_data: List[HistoricalWeatherData], 
        target_date: date
    ) -> ClimateNormal:
        """Calculate climate normal using advanced smoothing and harmonic analysis"""
        
        target_doy = target_date.timetuple().tm_yday
        
        # Use adaptive window size based on data density
        base_window = 15
        data_density = len(historical_data) / (365 * 5)  # Assume 5-year target
        adaptive_window = int(base_window / max(0.5, data_density))
        adaptive_window = max(7, min(30, adaptive_window))  # Constrain to reasonable range
        
        # Find all historical data within adaptive window
        window_data = []
        
        for record in historical_data:
            record_doy = record.date.timetuple().tm_yday
            
            # Handle year boundary with circular distance
            day_diff = min(
                abs(record_doy - target_doy),
                abs(record_doy - target_doy - 365),
                abs(record_doy - target_doy + 365)
            )
            
            if day_diff <= adaptive_window:
                # Apply distance-based weighting (closer days get more weight)
                weight = np.exp(-day_diff**2 / (2 * (adaptive_window/3)**2))  # Gaussian weighting
                window_data.append((record, weight))
        
        if not window_data:
            raise ValueError(f"No historical data found for day of year {target_doy}")
        
        # Calculate weighted climatological normals
        records, weights = zip(*window_data)
        weights = np.array(weights)
        weights = weights / weights.sum()  # Normalize weights
        
        # Use robust statistics to handle outliers
        temp_max_values = np.array([d.temperature_max for d in records])
        temp_min_values = np.array([d.temperature_min for d in records])
        precip_values = np.array([d.precipitation for d in records])
        humidity_values = np.array([d.humidity for d in records])
        wind_values = np.array([d.wind_speed for d in records])
        
        # Calculate weighted medians and means for robustness
        temp_max_normal = self._weighted_percentile(temp_max_values, weights, 50)  # Weighted median
        temp_min_normal = self._weighted_percentile(temp_min_values, weights, 50)
        
        # For precipitation, use both median and probability
        precip_normal = self._weighted_percentile(precip_values, weights, 50)
        precip_prob = np.sum(weights[precip_values > 0.1]) * 100  # Weighted probability
        
        # For humidity and wind, use weighted means with outlier filtering
        humidity_normal = np.average(humidity_values, weights=weights)
        wind_normal = np.average(wind_values, weights=weights)
        
        # Apply harmonic smoothing for seasonal consistency
        smoothed_temps = self._apply_harmonic_smoothing(
            target_doy, temp_max_normal, temp_min_normal
        )
        
        return ClimateNormal(
            date=target_date,
            temperature_max_normal=float(smoothed_temps['temp_max']),
            temperature_min_normal=float(smoothed_temps['temp_min']),
            precipitation_normal=float(precip_normal),
            humidity_normal=float(np.clip(humidity_normal, 0, 100)),
            wind_speed_normal=float(wind_normal),
            precipitation_probability_normal=float(min(100, max(0, precip_prob)))
        )

    def _weighted_percentile(self, values: np.ndarray, weights: np.ndarray, percentile: float) -> float:
        """Calculate weighted percentile"""
        sorted_indices = np.argsort(values)
        sorted_values = values[sorted_indices]
        sorted_weights = weights[sorted_indices]
        
        # Cumulative weights
        cum_weights = np.cumsum(sorted_weights)
        cum_weights = cum_weights / cum_weights[-1]  # Normalize to 0-1
        
        # Find percentile position
        target = percentile / 100.0
        
        # Interpolate to find value at target percentile
        if target <= cum_weights[0]:
            return float(sorted_values[0])
        elif target >= cum_weights[-1]:
            return float(sorted_values[-1])
        else:
            # Linear interpolation
            idx = np.searchsorted(cum_weights, target)
            if idx > 0 and cum_weights[idx] != cum_weights[idx-1]:
                # Interpolate between adjacent values
                weight_diff = cum_weights[idx] - cum_weights[idx-1]
                value_diff = sorted_values[idx] - sorted_values[idx-1]
                offset = (target - cum_weights[idx-1]) / weight_diff
                return float(sorted_values[idx-1] + offset * value_diff)
            else:
                return float(sorted_values[idx])

    def _apply_harmonic_smoothing(
        self, 
        target_doy: int, 
        temp_max: float, 
        temp_min: float
    ) -> Dict[str, float]:
        """Apply harmonic analysis for seasonal temperature smoothing"""
        
        # Basic harmonic components for mid-latitude climate
        # Annual cycle: peak summer (day ~200), minimum winter (day ~20)
        annual_phase_max = 200  # Peak summer
        annual_phase_min = 20   # Peak winter
        
        # Calculate seasonal adjustments
        annual_cycle_max = np.cos(2 * np.pi * (target_doy - annual_phase_max) / 365)
        annual_cycle_min = np.cos(2 * np.pi * (target_doy - annual_phase_min) / 365)
        
        # Semi-annual cycle (mild effects)
        semi_annual = 0.5 * np.cos(4 * np.pi * target_doy / 365)
        
        # Apply subtle harmonic corrections (±1°C max adjustment)
        temp_max_adj = temp_max + 0.5 * annual_cycle_max + 0.3 * semi_annual
        temp_min_adj = temp_min + 0.5 * annual_cycle_min + 0.2 * semi_annual
        
        return {
            'temp_max': temp_max_adj,
            'temp_min': temp_min_adj
        }
    
    def calculate_seasonal_trends(
        self, 
        historical_data: List[HistoricalWeatherData]
    ) -> Dict[str, Any]:
        """Analyze seasonal patterns and trends"""
        
        df = pd.DataFrame([
            {
                'date': d.date,
                'doy': d.date.timetuple().tm_yday,
                'year': d.date.year,
                'month': d.date.month,
                'temp_max': d.temperature_max,
                'temp_min': d.temperature_min,
                'precipitation': d.precipitation,
                'humidity': d.humidity,
                'wind_speed': d.wind_speed
            }
            for d in historical_data
        ])
        
        # Calculate annual cycles
        monthly_means = df.groupby('month').agg({
            'temp_max': 'mean',
            'temp_min': 'mean',
            'precipitation': 'mean',
            'humidity': 'mean',
            'wind_speed': 'mean'
        }).round(2)
        
        # Calculate trends over years
        yearly_means = df.groupby('year').agg({
            'temp_max': 'mean',
            'temp_min': 'mean',
            'precipitation': 'sum',
            'humidity': 'mean',
            'wind_speed': 'mean'
        })
        
        trends = {}
        for param in ['temp_max', 'temp_min', 'precipitation', 'humidity', 'wind_speed']:
            slope, intercept, r_value, p_value, std_err = stats.linregress(
                yearly_means.index, yearly_means[param]
            )
            trends[param] = {
                'slope': float(slope),
                'r_squared': float(r_value**2),
                'p_value': float(p_value),
                'trend_per_decade': float(slope * 10)
            }
        
        return {
            'monthly_climatology': monthly_means.to_dict(),
            'annual_trends': trends,
            'data_years': sorted(df['year'].unique().tolist())
        }
    
    def persistence_forecast(
        self, 
        recent_data: List[HistoricalWeatherData], 
        forecast_date: date,
        days_ahead: int = 1
    ) -> Dict[str, float]:
        """Simple persistence forecasting - recent conditions continue"""
        
        if not recent_data:
            raise ValueError("No recent data available for persistence forecast")
        
        # Use last 7 days for persistence, with more weight on recent days
        recent_data = sorted(recent_data, key=lambda x: x.date, reverse=True)[:7]
        
        weights = np.exp(-0.2 * np.arange(len(recent_data)))  # Exponential decay
        weights = weights / weights.sum()
        
        temp_max = sum(w * d.temperature_max for w, d in zip(weights, recent_data))
        temp_min = sum(w * d.temperature_min for w, d in zip(weights, recent_data))
        precipitation = sum(w * d.precipitation for w, d in zip(weights, recent_data))
        humidity = sum(w * d.humidity for w, d in zip(weights, recent_data))
        wind_speed = sum(w * d.wind_speed for w, d in zip(weights, recent_data))
        
        # Reduce confidence for longer forecast periods
        confidence_decay = max(0.3, 1.0 - (days_ahead - 1) * 0.1)
        
        return {
            'temp_max': float(temp_max),
            'temp_min': float(temp_min),
            'precipitation': float(precipitation),
            'humidity': float(humidity),
            'wind_speed': float(wind_speed),
            'confidence': confidence_decay
        }
    
    def analog_forecast(
        self, 
        historical_data: List[HistoricalWeatherData],
        recent_conditions: List[HistoricalWeatherData],
        forecast_date: date
    ) -> Dict[str, float]:
        """Advanced analog forecasting using multi-dimensional pattern matching"""
        
        if len(recent_conditions) < 5:
            return self.persistence_forecast(recent_conditions, forecast_date)
        
        # Use last 5 days for pattern matching
        recent_pattern = recent_conditions[-5:]
        target_doy = forecast_date.timetuple().tm_yday
        
        # Create multi-dimensional pattern signature
        pattern_features = self._extract_pattern_features(recent_pattern)
        
        best_matches = []
        min_sequence_length = 6  # Need 5 days + 1 forecast day
        
        # Search through historical data for similar patterns
        for i in range(len(historical_data) - min_sequence_length):
            hist_sequence = historical_data[i:i+5]
            
            # Seasonal filtering - allow wider window but penalize distant seasons
            hist_doy = hist_sequence[0].date.timetuple().tm_yday
            seasonal_distance = min(abs(hist_doy - target_doy), 365 - abs(hist_doy - target_doy))
            
            if seasonal_distance > 60:  # Skip very different seasons
                continue
            
            # Extract features from historical sequence
            hist_features = self._extract_pattern_features(hist_sequence)
            
            # Calculate multi-dimensional similarity
            similarity_score = self._calculate_pattern_similarity(
                pattern_features, hist_features, seasonal_distance
            )
            
            if similarity_score > 0.25:  # Threshold for acceptable analog
                # Get the day that followed this pattern
                if i + 5 < len(historical_data):
                    next_day = historical_data[i + 5]
                    best_matches.append((similarity_score, next_day, seasonal_distance))
        
        if not best_matches:
            return self.persistence_forecast(recent_conditions, forecast_date)
        
        # Sort by similarity and select top matches
        best_matches.sort(key=lambda x: x[0], reverse=True)
        top_matches = best_matches[:min(8, len(best_matches))]
        
        # Weight matches by similarity and seasonal proximity
        weights = []
        for similarity, _, seasonal_dist in top_matches:
            # Combine similarity with seasonal proximity
            seasonal_weight = np.exp(-seasonal_dist / 30.0)  # Decay over 30 days
            combined_weight = similarity * (0.7 + 0.3 * seasonal_weight)
            weights.append(combined_weight)
        
        weights = np.array(weights)
        weights = weights / weights.sum()
        
        # Calculate weighted forecast
        temp_max = sum(w * match[1].temperature_max for w, match in zip(weights, top_matches))
        temp_min = sum(w * match[1].temperature_min for w, match in zip(weights, top_matches))
        precipitation = sum(w * match[1].precipitation for w, match in zip(weights, top_matches))
        humidity = sum(w * match[1].humidity for w, match in zip(weights, top_matches))
        wind_speed = sum(w * match[1].wind_speed for w, match in zip(weights, top_matches))
        
        # Calculate confidence based on match quality and consistency
        confidence = self._calculate_analog_confidence(top_matches, weights)
        
        return {
            'temp_max': float(temp_max),
            'temp_min': float(temp_min),
            'precipitation': float(precipitation),
            'humidity': float(humidity),
            'wind_speed': float(wind_speed),
            'confidence': float(confidence)
        }

    def _extract_pattern_features(self, sequence: List[HistoricalWeatherData]) -> Dict[str, float]:
        """Extract meteorologically relevant features from weather sequence"""
        
        temps_max = [d.temperature_max for d in sequence]
        temps_min = [d.temperature_min for d in sequence]
        precips = [d.precipitation for d in sequence]
        humidities = [d.humidity for d in sequence]
        wind_speeds = [d.wind_speed for d in sequence]
        
        return {
            # Temperature features
            'temp_mean': np.mean(temps_max + temps_min),
            'temp_trend': np.polyfit(range(len(temps_max)), temps_max, 1)[0],  # Linear trend
            'temp_range_avg': np.mean([tmax - tmin for tmax, tmin in zip(temps_max, temps_min)]),
            'temp_variability': np.std(temps_max + temps_min),
            
            # Precipitation features
            'precip_total': np.sum(precips),
            'precip_intensity': np.mean([p for p in precips if p > 0.1]) if any(p > 0.1 for p in precips) else 0,
            'wet_days': len([p for p in precips if p > 0.1]),
            'precip_trend': np.polyfit(range(len(precips)), precips, 1)[0],
            
            # Atmospheric features
            'humidity_mean': np.mean(humidities),
            'humidity_trend': np.polyfit(range(len(humidities)), humidities, 1)[0],
            'wind_mean': np.mean(wind_speeds),
            'wind_variability': np.std(wind_speeds),
            
            # Synoptic patterns
            'pressure_tendency': self._estimate_pressure_tendency(sequence),
            'weather_regime': self._classify_weather_regime(sequence)
        }

    def _calculate_pattern_similarity(
        self, 
        pattern1: Dict[str, float], 
        pattern2: Dict[str, float],
        seasonal_distance: int
    ) -> float:
        """Calculate similarity between two weather patterns"""
        
        # Define feature weights based on meteorological importance
        feature_weights = {
            'temp_mean': 0.20,
            'temp_trend': 0.15,
            'temp_range_avg': 0.10,
            'temp_variability': 0.08,
            'precip_total': 0.15,
            'precip_intensity': 0.10,
            'wet_days': 0.08,
            'humidity_mean': 0.07,
            'wind_mean': 0.07
        }
        
        similarity_sum = 0.0
        weight_sum = 0.0
        
        for feature, weight in feature_weights.items():
            if feature in pattern1 and feature in pattern2:
                val1, val2 = pattern1[feature], pattern2[feature]
                
                # Calculate normalized difference
                if feature == 'temp_mean':
                    diff = abs(val1 - val2) / 20.0  # Normalize by 20°C
                elif feature.startswith('precip'):
                    diff = abs(val1 - val2) / max(10.0, max(val1, val2) + 1)  # Adaptive normalization
                elif feature.startswith('humidity'):
                    diff = abs(val1 - val2) / 50.0  # Normalize by 50%
                elif feature.startswith('wind'):
                    diff = abs(val1 - val2) / 15.0  # Normalize by 15 km/h
                else:
                    diff = abs(val1 - val2) / (abs(val1) + abs(val2) + 1)  # Relative difference
                
                # Convert difference to similarity (0 to 1)
                feature_similarity = np.exp(-diff)
                similarity_sum += weight * feature_similarity
                weight_sum += weight
        
        if weight_sum == 0:
            return 0.0
        
        base_similarity = similarity_sum / weight_sum
        
        # Apply seasonal penalty
        seasonal_penalty = np.exp(-seasonal_distance / 45.0)  # Decay over 45 days
        
        return base_similarity * (0.8 + 0.2 * seasonal_penalty)

    def _estimate_pressure_tendency(self, sequence: List[HistoricalWeatherData]) -> float:
        """Estimate pressure tendency from temperature and humidity trends"""
        
        temps = [d.temperature_max + d.temperature_min for d in sequence]
        humidities = [d.humidity for d in sequence]
        
        # Simple proxy: rising temperatures and falling humidity suggest rising pressure
        temp_trend = np.polyfit(range(len(temps)), temps, 1)[0]
        humid_trend = np.polyfit(range(len(humidities)), humidities, 1)[0]
        
        # Combine trends (positive = rising pressure tendency)
        return temp_trend * 0.1 - humid_trend * 0.02

    def _classify_weather_regime(self, sequence: List[HistoricalWeatherData]) -> float:
        """Classify general weather regime (0=stable, 1=active)"""
        
        temp_var = np.std([d.temperature_max for d in sequence])
        precip_days = len([d for d in sequence if d.precipitation > 0.1])
        wind_mean = np.mean([d.wind_speed for d in sequence])
        
        # Active weather: high variability, precipitation, strong winds
        activity_score = (temp_var / 5.0 + precip_days / len(sequence) + wind_mean / 20.0) / 3.0
        
        return min(1.0, activity_score)

    def _calculate_analog_confidence(
        self, 
        matches: List[Tuple], 
        weights: np.ndarray
    ) -> float:
        """Calculate confidence based on analog match quality"""
        
        if len(matches) == 0:
            return 0.3
        
        # Base confidence from similarity scores
        similarities = [match[0] for match in matches]
        base_confidence = np.average(similarities, weights=weights)
        
        # Boost confidence if we have many good matches
        match_count_boost = min(0.2, len(matches) * 0.03)
        
        # Reduce confidence if matches are inconsistent
        match_outcomes = [match[1] for match in matches]
        temp_consistency = 1.0 - np.std([m.temperature_max for m in match_outcomes]) / 10.0
        temp_consistency = max(0.0, temp_consistency)
        
        final_confidence = (base_confidence + match_count_boost) * (0.7 + 0.3 * temp_consistency)
        
        return max(0.2, min(0.95, final_confidence))
    
    def determine_weather_conditions(
        self, 
        temp_max: float, 
        temp_min: float, 
        precipitation: float, 
        humidity: float, 
        wind_speed: float
    ) -> WeatherCondition:
        """Determine general weather conditions from parameters"""
        
        if precipitation > 20:
            return WeatherCondition.HEAVY_RAIN
        elif precipitation > 5:
            return WeatherCondition.MODERATE_RAIN
        elif precipitation > 0.5:
            return WeatherCondition.LIGHT_RAIN
        elif wind_speed > 15:
            return WeatherCondition.WINDY
        elif humidity > 90:
            return WeatherCondition.FOG
        elif humidity < 30:
            if (temp_max + temp_min) / 2 > 25:
                return WeatherCondition.SUNNY
            else:
                return WeatherCondition.PARTLY_CLOUDY
        elif humidity > 80:
            return WeatherCondition.OVERCAST
        elif humidity > 60:
            return WeatherCondition.CLOUDY
        else:
            return WeatherCondition.PARTLY_CLOUDY
    
    def determine_wind_direction(
        self, 
        historical_data: List[HistoricalWeatherData], 
        forecast_date: date
    ) -> WindDirection:
        """Determine most likely wind direction based on climatology"""
        
        # Get seasonal wind direction patterns
        target_month = forecast_date.month
        
        seasonal_directions = []
        for record in historical_data:
            if (record.date.month == target_month or 
                abs(record.date.month - target_month) <= 1) and record.wind_direction:
                seasonal_directions.append(record.wind_direction)
        
        if seasonal_directions:
            # Return most common direction for the season
            from collections import Counter
            direction_counts = Counter(seasonal_directions)
            return direction_counts.most_common(1)[0][0]
        
        # Default to prevailing wind direction if no seasonal data
        return WindDirection.W  # Westerly winds are most common globally
    
    def calculate_confidence_level(
        self, 
        forecast_method: str, 
        days_ahead: int, 
        data_quality: float,
        pattern_strength: float = 0.5
    ) -> ConfidenceLevel:
        """Calculate confidence level for forecast"""
        
        # Base confidence by method (climatology is actually quite reliable for seasonal patterns)
        method_confidence = {
            'persistence': 0.85,
            'climatology': 0.80,  # Higher base confidence for climatology
            'analog': 0.75,
            'trend': 0.65
        }
        
        base_conf = method_confidence.get(forecast_method, 0.6)
        
        # More gradual time decay for climatology (it's designed for longer forecasts)
        if forecast_method == 'climatology':
            # Climatology maintains better confidence over time
            time_decay = max(0.6, 1.0 - (days_ahead - 1) * 0.008)  # Slower decay
        else:
            time_decay = max(0.3, 1.0 - (days_ahead - 1) * 0.015)
        
        # Data quality factor (NASA data is high quality)
        data_factor = min(1.0, data_quality / 85.0)  # Normalize to 85% as baseline
        
        # Pattern strength factor
        pattern_factor = max(0.6, pattern_strength)  # Higher minimum
        
        # Use weighted average instead of multiplication to avoid too low values
        weights = [0.4, 0.3, 0.2, 0.1]  # base_conf, time_decay, data_factor, pattern_factor
        factors = [base_conf, time_decay, data_factor, pattern_factor]
        
        overall_confidence = sum(w * f for w, f in zip(weights, factors))
        
        # Adjust thresholds for climatology methods
        if forecast_method == 'climatology':
            if overall_confidence > 0.75:
                return ConfidenceLevel.HIGH
            elif overall_confidence > 0.60:
                return ConfidenceLevel.MEDIUM
            else:
                return ConfidenceLevel.LOW
        else:
            if overall_confidence > 0.80:
                return ConfidenceLevel.HIGH
            elif overall_confidence > 0.65:
                return ConfidenceLevel.MEDIUM
            else:
                return ConfidenceLevel.LOW
    
    def seasonal_decomposition(
        self, 
        historical_data: List[HistoricalWeatherData]
    ) -> Dict[str, Any]:
        """Decompose time series into trend, seasonal, and residual components"""
        
        df = pd.DataFrame([
            {
                'date': d.date,
                'temp_max': d.temperature_max,
                'temp_min': d.temperature_min,
                'precipitation': d.precipitation
            }
            for d in historical_data
        ])
        
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)
        
        components = {}
        
        for param in ['temp_max', 'temp_min', 'precipitation']:
            # Simple seasonal decomposition
            # Calculate annual mean for trend
            yearly_means = df.groupby(df.index.year)[param].mean()
            
            # Calculate monthly seasonal component
            monthly_means = df.groupby(df.index.month)[param].mean()
            overall_mean = df[param].mean()
            seasonal_component = monthly_means - overall_mean
            
            # Linear trend
            years = np.array([d.year for d in df.index])
            values = df[param].values
            slope, intercept = np.polyfit(years, values, 1)
            
            components[param] = {
                'trend_slope': float(slope),
                'trend_intercept': float(intercept),
                'seasonal_cycle': seasonal_component.to_dict(),
                'overall_mean': float(overall_mean)
            }
        
        return components