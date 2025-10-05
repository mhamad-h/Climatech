import asyncio
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import numpy as np
import logging

from services.climatology_service import ClimatologyService
from services.historical_data_service import HistoricalDataService
from models.weather_data import (
    WeatherForecast, MonthlyOutlook, ClimateNormal, 
    HistoricalWeatherData, WeatherCondition, WindDirection, ConfidenceLevel,
    ExtendedForecastResponse
)
from models.forecast_models import LocationClimateProfile

logger = logging.getLogger(__name__)


class ForecastService:
    """Main service for generating climatology-based weather forecasts"""
    
    def __init__(self):
        self.climatology_service = ClimatologyService()
        self.historical_service = HistoricalDataService()
        self.max_forecast_days = 180  # 6 months
    
    async def generate_extended_forecast(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        forecast_days: int,
        include_climate_context: bool = True
    ) -> ExtendedForecastResponse:
        """Generate extended forecast up to 6 months"""
        
        if forecast_days > self.max_forecast_days:
            raise ValueError(f"Forecast period cannot exceed {self.max_forecast_days} days")
        
        logger.info(f"Generating {forecast_days}-day forecast for {latitude}, {longitude}")
        
        # Fetch historical data
        historical_data = await self.historical_service.get_last_n_years_data(
            latitude, longitude, years=5
        )
        
        if not historical_data:
            raise ValueError("No historical data available for this location")
        
        # Get recent conditions for persistence forecasting
        recent_data = await self.historical_service.get_recent_conditions(
            latitude, longitude, days=10
        )
        
        # Calculate data quality
        total_expected_days = 5 * 365  # 5 years
        data_completeness = self.historical_service.calculate_data_completeness(
            historical_data, total_expected_days
        )
        data_quality = self.historical_service.validate_data_quality(historical_data)
        
        # Generate daily forecasts
        daily_forecasts = []
        climate_normals = []
        
        for day_offset in range(forecast_days):
            forecast_date = start_date + timedelta(days=day_offset)
            
            # Generate forecast for this day
            forecast = await self._generate_daily_forecast(
                latitude, longitude, forecast_date, 
                historical_data, recent_data, day_offset + 1
            )
            daily_forecasts.append(forecast)
            
            # Calculate climate normal if requested
            if include_climate_context:
                try:
                    climate_normal = self.climatology_service.calculate_day_of_year_climatology(
                        historical_data, forecast_date
                    )
                    climate_normals.append(climate_normal)
                except ValueError:
                    # Skip if no climate normal available for this date
                    pass
        
        # Generate monthly outlooks
        monthly_outlooks = self._generate_monthly_outlooks(daily_forecasts, start_date)
        
        # Calculate overall confidence
        avg_confidence = self._calculate_overall_confidence(daily_forecasts, data_quality["overall_quality"])
        
        # Generate seasonal outlook
        seasonal_outlook = self._generate_seasonal_outlook(historical_data, start_date, forecast_days)
        
        # Detect notable patterns
        notable_patterns = self._detect_notable_patterns(historical_data, daily_forecasts)
        
        end_date = start_date + timedelta(days=forecast_days - 1)
        
        return ExtendedForecastResponse(
            location={"latitude": latitude, "longitude": longitude},
            forecast_generated=datetime.utcnow(),
            forecast_period={"start_date": start_date, "end_date": end_date},
            daily_forecasts=daily_forecasts,
            monthly_outlooks=monthly_outlooks,
            climate_normals=climate_normals if include_climate_context else None,
            overall_confidence=avg_confidence,
            data_completeness=data_completeness,
            seasonal_outlook=seasonal_outlook,
            notable_patterns=notable_patterns
        )
    
    async def _generate_daily_forecast(
        self,
        latitude: float,
        longitude: float,
        forecast_date: date,
        historical_data: List[HistoricalWeatherData],
        recent_data: List[HistoricalWeatherData],
        days_ahead: int
    ) -> WeatherForecast:
        """Generate forecast for a single day"""
        
        # Use different methods based on forecast horizon
        if days_ahead <= 7:
            # Short-range: primarily persistence with climatology
            persistence_result = self.climatology_service.persistence_forecast(
                recent_data, forecast_date, days_ahead
            )
            
            analog_result = self.climatology_service.analog_forecast(
                historical_data, recent_data, forecast_date
            )
            
            # Blend persistence and analog methods
            if days_ahead <= 3:
                weight_persistence = 0.7
                weight_analog = 0.3
            else:
                weight_persistence = 0.4
                weight_analog = 0.6
            
            temp_max = (weight_persistence * persistence_result["temp_max"] + 
                       weight_analog * analog_result["temp_max"])
            temp_min = (weight_persistence * persistence_result["temp_min"] + 
                       weight_analog * analog_result["temp_min"])
            
            # Better precipitation handling with seasonal context
            precip_raw = (weight_persistence * persistence_result["precipitation"] + 
                         weight_analog * analog_result["precipitation"])
            
            # Apply realistic constraints and seasonal adjustment
            seasonal_precip = self._get_seasonal_precipitation_normal(historical_data, forecast_date)
            precipitation = max(0.0, min(precip_raw * 0.6 + seasonal_precip * 0.4, 80.0))
            
            # Apply realistic constraints to other parameters
            humidity = np.clip(
                weight_persistence * persistence_result["humidity"] + 
                weight_analog * analog_result["humidity"], 
                15.0, 100.0
            )
            base_wind = (weight_persistence * persistence_result["wind_speed"] + 
                        weight_analog * analog_result["wind_speed"])
            wind_speed = self._calculate_realistic_wind_speed(
                historical_data, forecast_date, base_wind
            )
            
            method_confidence = (persistence_result["confidence"] + analog_result["confidence"]) / 2
            
        else:
            # Long-range: primarily climatology
            try:
                climate_normal = self.climatology_service.calculate_day_of_year_climatology(
                    historical_data, forecast_date
                )
                
                # Add seasonal trends
                seasonal_trends = self.climatology_service.calculate_seasonal_trends(historical_data)
                
                # Apply trend adjustments
                current_year = forecast_date.year
                years_since_base = current_year - min(d.date.year for d in historical_data)
                
                temp_trend_adjustment = (seasonal_trends["annual_trends"]["temp_max"]["slope"] * 
                                       years_since_base)
                
                temp_max = climate_normal.temperature_max_normal + temp_trend_adjustment
                temp_min = climate_normal.temperature_min_normal + temp_trend_adjustment
                
                # Better precipitation handling for long-range forecasts
                base_precipitation = climate_normal.precipitation_normal
                seasonal_variance = self._calculate_seasonal_precipitation_variance(historical_data, forecast_date)
                precipitation = max(0.0, base_precipitation * (0.8 + seasonal_variance * 0.4))
                
                humidity = np.clip(climate_normal.humidity_normal, 20.0, 100.0)
                wind_speed = self._calculate_realistic_wind_speed(
                    historical_data, forecast_date, climate_normal.wind_speed_normal
                )
                
                # Reduced confidence for long-range forecasts
                method_confidence = max(0.3, 0.8 - (days_ahead - 7) * 0.01)
                
            except ValueError:
                # Fallback to seasonal averages if no specific climatology available
                month_data = [d for d in historical_data if d.date.month == forecast_date.month]
                
                if month_data:
                    temp_max = np.mean([d.temperature_max for d in month_data])
                    temp_min = np.mean([d.temperature_min for d in month_data])
                    precipitation = np.mean([d.precipitation for d in month_data])
                    humidity = np.mean([d.humidity for d in month_data])
                    base_wind = np.mean([d.wind_speed for d in month_data])
                    wind_speed = self._calculate_realistic_wind_speed(
                        historical_data, forecast_date, base_wind
                    )
                else:
                    # Last resort: use overall averages
                    temp_max = np.mean([d.temperature_max for d in historical_data])
                    temp_min = np.mean([d.temperature_min for d in historical_data])
                    precipitation = np.mean([d.precipitation for d in historical_data])
                    humidity = np.mean([d.humidity for d in historical_data])
                    base_wind = np.mean([d.wind_speed for d in historical_data])
                    wind_speed = self._calculate_realistic_wind_speed(
                        historical_data, forecast_date, base_wind
                    )
                
                method_confidence = 0.3
        
        # Calculate climate context
        try:
            climate_normal = self.climatology_service.calculate_day_of_year_climatology(
                historical_data, forecast_date
            )
            temp_vs_normal = (temp_max + temp_min) / 2 - (
                climate_normal.temperature_max_normal + climate_normal.temperature_min_normal) / 2
            precip_vs_normal = ((precipitation / max(0.1, climate_normal.precipitation_normal)) - 1) * 100
        except ValueError:
            temp_vs_normal = 0.0
            precip_vs_normal = 0.0
        
        # Determine weather conditions
        conditions = self.climatology_service.determine_weather_conditions(
            temp_max, temp_min, precipitation, humidity, wind_speed
        )
        
        # Determine wind direction
        wind_direction = self.climatology_service.determine_wind_direction(
            historical_data, forecast_date
        )

        
        # Calculate confidence levels
        data_quality_score = 90.0  # NASA POWER data is high quality
        
        temp_confidence = self.climatology_service.calculate_confidence_level(
            "climatology", days_ahead, data_quality_score, method_confidence
        )
        precip_confidence = self.climatology_service.calculate_confidence_level(
            "climatology", days_ahead, data_quality_score, method_confidence * 0.85  # Slightly lower for precipitation
        )
        
        # Calculate precipitation probability using climatological approach
        precip_probability = self._calculate_precipitation_probability(
            historical_data, forecast_date, precipitation
        )
        
        return WeatherForecast(
            date=forecast_date,
            temperature_max=round(float(temp_max), 1),
            temperature_min=round(float(temp_min), 1),
            temperature_max_confidence=temp_confidence,
            temperature_min_confidence=temp_confidence,
            precipitation_amount=round(float(precipitation), 1),
            precipitation_probability=round(precip_probability, 1),
            precipitation_confidence=precip_confidence,
            humidity=round(float(humidity), 1),
            humidity_confidence=temp_confidence,  # Similar confidence to temperature
            wind_speed=round(float(wind_speed), 1),
            wind_direction=wind_direction,
            wind_confidence=precip_confidence,  # Lower confidence for wind
            conditions=conditions,
            conditions_confidence=precip_confidence,
            temperature_vs_normal=round(temp_vs_normal, 1),
            precipitation_vs_normal=round(precip_vs_normal, 1)
        )
    
    def _generate_monthly_outlooks(
        self, 
        daily_forecasts: List[WeatherForecast], 
        start_date: date
    ) -> List[MonthlyOutlook]:
        """Generate monthly outlook summaries from daily forecasts"""
        
        monthly_data = {}
        
        # Group forecasts by month
        for forecast in daily_forecasts:
            month_key = (forecast.date.year, forecast.date.month)
            
            if month_key not in monthly_data:
                monthly_data[month_key] = []
            
            monthly_data[month_key].append(forecast)
        
        monthly_outlooks = []
        
        for (year, month), forecasts in monthly_data.items():
            if len(forecasts) < 5:  # Skip months with too few days
                continue
            
            # Calculate monthly averages
            avg_temp_max = np.mean([f.temperature_max for f in forecasts])
            avg_temp_min = np.mean([f.temperature_min for f in forecasts])
            total_precipitation = sum([f.precipitation_amount for f in forecasts])
            avg_humidity = np.mean([f.humidity for f in forecasts])
            avg_wind_speed = np.mean([f.wind_speed for f in forecasts])
            
            # Calculate vs normal
            temp_vs_normal = np.mean([f.temperature_vs_normal for f in forecasts])
            precip_vs_normal = np.mean([f.precipitation_vs_normal for f in forecasts])
            
            # Determine dominant conditions
            conditions_count = {}
            for f in forecasts:
                conditions_count[f.conditions] = conditions_count.get(f.conditions, 0) + 1
            
            dominant_conditions = sorted(conditions_count.keys(), 
                                       key=lambda x: conditions_count[x], 
                                       reverse=True)[:3]
            
            # Calculate confidence
            confidences = []
            for f in forecasts:
                conf_values = {
                    ConfidenceLevel.HIGH: 3,
                    ConfidenceLevel.MEDIUM: 2,
                    ConfidenceLevel.LOW: 1
                }
                avg_conf = (conf_values[f.temperature_max_confidence] + 
                           conf_values[f.precipitation_confidence]) / 2
                confidences.append(avg_conf)
            
            avg_conf_value = np.mean(confidences)
            if avg_conf_value > 2.5:
                month_confidence = ConfidenceLevel.HIGH
            elif avg_conf_value > 1.5:
                month_confidence = ConfidenceLevel.MEDIUM
            else:
                month_confidence = ConfidenceLevel.LOW
            
            monthly_outlooks.append(MonthlyOutlook(
                year=year,
                month=month,
                avg_temperature_max=round(avg_temp_max, 1),
                avg_temperature_min=round(avg_temp_min, 1),
                total_precipitation=round(total_precipitation, 1),
                avg_humidity=round(avg_humidity, 1),
                avg_wind_speed=round(avg_wind_speed, 1),
                temperature_vs_normal=round(temp_vs_normal, 1),
                precipitation_vs_normal=round(precip_vs_normal, 1),
                confidence=month_confidence,
                dominant_conditions=dominant_conditions
            ))
        
        return monthly_outlooks
    
    def _calculate_overall_confidence(
        self, 
        daily_forecasts: List[WeatherForecast], 
        data_quality: float
    ) -> ConfidenceLevel:
        """Calculate overall forecast confidence"""
        
        confidence_scores = []
        confidence_mapping = {
            ConfidenceLevel.HIGH: 3,
            ConfidenceLevel.MEDIUM: 2,
            ConfidenceLevel.LOW: 1
        }
        
        for forecast in daily_forecasts:
            # Average confidence across parameters
            temp_conf = confidence_mapping[forecast.temperature_max_confidence]
            precip_conf = confidence_mapping[forecast.precipitation_confidence]
            avg_conf = (temp_conf + precip_conf) / 2
            confidence_scores.append(avg_conf)
        
        overall_avg = np.mean(confidence_scores)
        
        # Adjust for data quality
        quality_factor = data_quality / 100.0
        adjusted_confidence = overall_avg * quality_factor
        
        if adjusted_confidence > 2.3:
            return ConfidenceLevel.HIGH
        elif adjusted_confidence > 1.7:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def _generate_seasonal_outlook(
        self, 
        historical_data: List[HistoricalWeatherData], 
        start_date: date, 
        forecast_days: int
    ) -> str:
        """Generate general seasonal outlook description"""
        
        # Determine seasons covered by forecast
        end_date = start_date + timedelta(days=forecast_days - 1)
        
        seasons = set()
        current_date = start_date
        while current_date <= end_date:
            month = current_date.month
            if month in [12, 1, 2]:
                seasons.add("winter")
            elif month in [3, 4, 5]:
                seasons.add("spring")
            elif month in [6, 7, 8]:
                seasons.add("summer")
            else:
                seasons.add("autumn")
            
            current_date += timedelta(days=32)  # Jump to next month
            current_date = current_date.replace(day=1)
        
        # Analyze historical trends for these seasons
        seasonal_trends = self.climatology_service.calculate_seasonal_trends(historical_data)
        
        outlook_parts = []
        
        if "winter" in seasons:
            temp_trend = seasonal_trends["annual_trends"]["temp_max"]["trend_per_decade"]
            if temp_trend > 0.5:
                outlook_parts.append("warmer than average winter conditions expected")
            elif temp_trend < -0.5:
                outlook_parts.append("cooler than average winter conditions expected")
            else:
                outlook_parts.append("near-normal winter temperatures expected")
        
        if "spring" in seasons:
            outlook_parts.append("typical spring transition patterns")
        
        if "summer" in seasons:
            outlook_parts.append("seasonal summer weather patterns")
        
        if "autumn" in seasons:
            outlook_parts.append("typical autumn cooling trends")
        
        return "; ".join(outlook_parts).capitalize() + "."
    
    def _detect_notable_patterns(
        self, 
        historical_data: List[HistoricalWeatherData],
        daily_forecasts: List[WeatherForecast]
    ) -> List[str]:
        """Detect notable climate patterns in the forecast"""
        
        patterns = []
        
        # Check for extended dry/wet periods
        consecutive_dry_days = 0
        consecutive_wet_days = 0
        
        for forecast in daily_forecasts:
            if forecast.precipitation_amount < 0.1:
                consecutive_dry_days += 1
                consecutive_wet_days = 0
            else:
                consecutive_wet_days += 1
                consecutive_dry_days = 0
            
            if consecutive_dry_days >= 14:
                patterns.append(f"Extended dry period forecast ({consecutive_dry_days} consecutive days)")
                consecutive_dry_days = 0  # Reset to avoid duplicate messages
            
            if consecutive_wet_days >= 7:
                patterns.append(f"Extended wet period forecast ({consecutive_wet_days} consecutive days)")
                consecutive_wet_days = 0
        
        # Check for significant temperature anomalies
        temp_anomalies = [f.temperature_vs_normal for f in daily_forecasts]
        avg_anomaly = np.mean(temp_anomalies)
        
        if avg_anomaly > 3:
            patterns.append(f"Significantly warmer than normal conditions (+{avg_anomaly:.1f}°C)")
        elif avg_anomaly < -3:
            patterns.append(f"Significantly cooler than normal conditions ({avg_anomaly:.1f}°C)")
        
        # Check for precipitation anomalies
        precip_anomalies = [f.precipitation_vs_normal for f in daily_forecasts]
        avg_precip_anomaly = np.mean(precip_anomalies)
        
        if avg_precip_anomaly > 50:
            patterns.append(f"Above normal precipitation expected (+{avg_precip_anomaly:.0f}%)")
        elif avg_precip_anomaly < -30:
            patterns.append(f"Below normal precipitation expected ({avg_precip_anomaly:.0f}%)")
        
        return patterns
    
    def _get_seasonal_precipitation_normal(
        self, 
        historical_data: List[HistoricalWeatherData], 
        forecast_date: date
    ) -> float:
        """Get seasonal precipitation normal for more accurate forecasting"""
        
        # Get data for the same month across all years
        month_data = [d for d in historical_data if d.date.month == forecast_date.month]
        
        if not month_data:
            return 0.0
        
        # Calculate median precipitation (more robust than mean for precipitation)
        precipitations = [d.precipitation for d in month_data if d.precipitation >= 0]
        
        if not precipitations:
            return 0.0
        
        # Use median to avoid outliers affecting the result
        median_precip = np.median(precipitations)
        
        # Apply day-of-month adjustment (early/mid/late month patterns)
        day_of_month = forecast_date.day
        if day_of_month <= 10:  # Early month
            adjustment = 0.9
        elif day_of_month <= 20:  # Mid month
            adjustment = 1.0
        else:  # Late month
            adjustment = 1.1
        
        return median_precip * adjustment
    
    def _calculate_seasonal_precipitation_variance(
        self, 
        historical_data: List[HistoricalWeatherData], 
        forecast_date: date
    ) -> float:
        """Calculate seasonal precipitation variance for better uncertainty modeling"""
        
        month_data = [d for d in historical_data if d.date.month == forecast_date.month]
        
        if len(month_data) < 3:
            return 0.2  # Default moderate variance
        
        precipitations = [d.precipitation for d in month_data if d.precipitation >= 0]
        
        if len(precipitations) < 3:
            return 0.2
        
        # Calculate coefficient of variation (normalized variance)
        mean_precip = np.mean(precipitations)
        std_precip = np.std(precipitations)
        
        if mean_precip <= 0:
            return 0.2
        
        cv = std_precip / mean_precip
        
        # Return normalized variance (0.0 to 1.0 range)
        return min(1.0, cv / 2.0)

    def _calculate_realistic_wind_speed(
        self,
        historical_data: List[HistoricalWeatherData],
        forecast_date: date,
        base_wind_speed: float
    ) -> float:
        """Calculate realistic wind speed using proper climatological methods."""
        
        month = forecast_date.month
        day_of_year = forecast_date.timetuple().tm_yday
        
        # Get historical wind data for the month
        month_data = [d for d in historical_data if d.date.month == month]
        
        if len(month_data) >= 10:
            # Use historical climatology approach
            return self._calculate_climatological_wind(month_data, forecast_date, base_wind_speed)
        else:
            # Use synthetic climatology based on location and season
            return self._calculate_synthetic_wind(forecast_date, base_wind_speed)

    def _calculate_climatological_wind(
        self,
        month_data: List[HistoricalWeatherData],
        forecast_date: date,
        base_wind_speed: float
    ) -> float:
        """Calculate wind using historical climatological patterns."""
        
        # Extract wind speeds and create climatology
        wind_speeds = [d.wind_speed for d in month_data if d.wind_speed > 0]
        
        if not wind_speeds:
            return self._calculate_synthetic_wind(forecast_date, base_wind_speed)
        
        # Calculate climatological statistics
        wind_mean = np.mean(wind_speeds)
        wind_median = np.median(wind_speeds)
        wind_std = np.std(wind_speeds)
        wind_p25 = np.percentile(wind_speeds, 25)
        wind_p75 = np.percentile(wind_speeds, 75)
        
        # Day-of-month variation (some days are typically windier)
        day_factor = 1.0 + 0.1 * np.sin(forecast_date.day * 2 * np.pi / 31)
        
        # Use persistence + climatology blend
        if base_wind_speed > 0:
            # Weight recent conditions with climatology (70% climo, 30% persistence)
            persistence_weight = 0.3
            climatology_weight = 0.7
            
            # Use median for stability, adjust with base wind trend
            if base_wind_speed > wind_median:
                # Recent winds higher than normal - trend toward upper quartile
                target_wind = wind_p75
            elif base_wind_speed < wind_median:
                # Recent winds lower than normal - trend toward lower quartile  
                target_wind = wind_p25
            else:
                # Recent winds normal - use median
                target_wind = wind_median
            
            calculated_wind = (persistence_weight * base_wind_speed + 
                             climatology_weight * target_wind) * day_factor
        else:
            # No persistence data - use pure climatology with seasonal adjustment
            calculated_wind = wind_median * day_factor
        
        # Add realistic daily variability based on historical standard deviation
        daily_var_factor = (forecast_date.day % 7) / 7.0  # 0 to 1
        daily_variation = (daily_var_factor - 0.5) * wind_std * 0.4  # ±20% of std dev
        
        final_wind = calculated_wind + daily_variation
        
        # Constrain to reasonable bounds based on historical data
        min_realistic = max(3.0, wind_p25 * 0.7)
        max_realistic = min(50.0, wind_p75 * 1.4)
        
        return max(min_realistic, min(max_realistic, final_wind))

    def _calculate_synthetic_wind(
        self,
        forecast_date: date,
        base_wind_speed: float
    ) -> float:
        """Calculate synthetic wind using meteorological principles when no historical data."""
        
        month = forecast_date.month
        day_of_year = forecast_date.timetuple().tm_yday
        
        # Seasonal cycle based on typical mid-latitude patterns
        seasonal_amplitude = 6.0  # km/h amplitude
        seasonal_mean = 15.0      # km/h annual mean
        
        # Peak windiness in late fall/winter (day ~330), minimum in summer (day ~200)
        seasonal_phase = 330  # Day of year for peak winds
        seasonal_wind = seasonal_mean + seasonal_amplitude * np.cos(
            2 * np.pi * (day_of_year - seasonal_phase) / 365.25
        )
        
        # Monthly fine-tuning based on typical patterns
        monthly_factors = {
            1: 1.2,   # January - Winter storm season
            2: 1.15,  # February - Still stormy
            3: 1.1,   # March - Transition, still windy
            4: 1.0,   # April - Spring, moderate
            5: 0.9,   # May - Spring, calming
            6: 0.8,   # June - Early summer, calm
            7: 0.75,  # July - Summer minimum
            8: 0.8,   # August - Late summer
            9: 0.9,   # September - Fall pickup
            10: 1.0,  # October - Fall winds increasing
            11: 1.1,  # November - Getting stormy
            12: 1.15  # December - Winter storm approach
        }
        
        monthly_factor = monthly_factors.get(month, 1.0)
        
        # Apply monthly adjustment
        adjusted_seasonal = seasonal_wind * monthly_factor
        
        # Daily variability based on synoptic patterns (deterministic for consistency)
        day_cycle = forecast_date.day % 10  # 10-day cycle
        daily_factor = 0.9 + 0.2 * np.sin(day_cycle * 2 * np.pi / 10)  # 0.9 to 1.1
        
        # Persistence influence if we have base wind speed
        if base_wind_speed > 0 and base_wind_speed < 50:
            # Blend persistence with climatology (40% persistence, 60% climatology)
            synthetic_wind = (0.4 * base_wind_speed + 0.6 * adjusted_seasonal) * daily_factor
        else:
            # Pure climatological estimate
            synthetic_wind = adjusted_seasonal * daily_factor
        
        # Add some terrain/local effects (day-to-day variation)
        terrain_effect = 2.0 * np.sin(forecast_date.toordinal() * 0.1)  # ±2 km/h
        
        final_wind = synthetic_wind + terrain_effect
        
        # Realistic bounds - typical range for most locations
        return max(5.0, min(35.0, final_wind))

    def _get_seasonal_wind_factor(self, month: int) -> float:
        """Get seasonal wind factor based on typical patterns."""
        
        # More moderate seasonal wind patterns (Northern Hemisphere)
        seasonal_factors = {
            1: 1.15,  # January - Winter, stronger winds
            2: 1.15,  # February - Winter, stronger winds  
            3: 1.05,  # March - Transition, moderate winds
            4: 1.0,   # April - Spring, moderate winds
            5: 0.95,  # May - Spring, slightly calmer
            6: 0.9,   # June - Early summer, calmer
            7: 0.9,   # July - Summer, calmer
            8: 0.9,   # August - Late summer, calmer
            9: 0.95,  # September - Early fall, increasing
            10: 1.0,  # October - Fall, moderate
            11: 1.05, # November - Late fall, increasing
            12: 1.15  # December - Early winter, stronger
        }
        
        return seasonal_factors.get(month, 1.0)

    def _get_seasonal_wind_base(self, month: int) -> float:
        """Get realistic wind speed base values for each month when no historical data."""
        
        # More realistic monthly wind speeds (km/h) for temperate climate
        seasonal_base = {
            1: 18.0,  # January - Winter storms, stronger winds
            2: 17.0,  # February - Still windy in winter
            3: 16.0,  # March - Transition, still breezy
            4: 14.0,  # April - Spring, moderate winds
            5: 12.0,  # May - Spring, calmer but still breezy
            6: 11.0,  # June - Early summer, lighter winds
            7: 10.0,  # July - Summer, lightest winds
            8: 11.0,  # August - Late summer, picking up
            9: 13.0,  # September - Fall transition, windier
            10: 15.0, # October - Fall, getting windier
            11: 16.0, # November - Late fall, windy
            12: 17.0  # December - Winter approaching, strong winds
        }
        
        return seasonal_base.get(month, 14.0)

    def _calculate_precipitation_probability(
        self,
        historical_data: List[HistoricalWeatherData],
        forecast_date: date,
        forecasted_precip: float
    ) -> float:
        """Calculate precipitation probability based on climatological patterns."""
        month = forecast_date.month
        
        # Get same month data
        same_month_data = [
            record for record in historical_data
            if record.date.month == month
        ]
        
        if not same_month_data:
            # Default probability based on forecasted amount
            if forecasted_precip < 0.1:
                return 10.0
            elif forecasted_precip < 1.0:
                return 30.0
            elif forecasted_precip < 5.0:
                return 60.0
            else:
                return 85.0
        
        # Count days with measurable precipitation (> 0.1mm)
        wet_days = sum(1 for record in same_month_data 
                      if record.precipitation > 0.1)
        total_days = len(same_month_data)
        
        # Base probability from climatology
        base_prob = (wet_days / total_days) * 100 if total_days > 0 else 20.0
        
        # Adjust based on forecasted amount
        if forecasted_precip < 0.1:
            # Very low precipitation
            probability = base_prob * 0.2
        elif forecasted_precip < 1.0:
            # Light precipitation
            probability = base_prob * 0.6
        elif forecasted_precip < 5.0:
            # Moderate precipitation
            probability = base_prob * 1.0
        elif forecasted_precip < 15.0:
            # Heavy precipitation
            probability = min(90.0, base_prob * 1.3)
        else:
            # Very heavy precipitation
            probability = min(95.0, base_prob * 1.5)
        
        return min(100.0, max(5.0, probability))

    def _calculate_precipitation_probability(
        self, 
        historical_data: List[HistoricalWeatherData], 
        forecast_date: date, 
        forecasted_precip: float
    ) -> float:
        """Calculate precipitation probability based on climatological patterns."""
        month_data = [d for d in historical_data if d.date.month == forecast_date.month]
        
        if not month_data:
            # Default probabilities based on forecasted amount
            if forecasted_precip < 0.1:
                return 10.0
            elif forecasted_precip < 1.0:
                return 30.0
            elif forecasted_precip < 5.0:
                return 60.0
            else:
                return 85.0
        
        # Count wet days (> 0.1mm precipitation)
        wet_days = sum(1 for d in month_data if d.precipitation > 0.1)
        total_days = len(month_data)
        
        # Base climatological probability
        base_prob = (wet_days / total_days) * 100 if total_days > 0 else 20.0
        
        # Adjust based on forecasted amount
        if forecasted_precip < 0.1:
            probability = base_prob * 0.2
        elif forecasted_precip < 1.0:
            probability = base_prob * 0.6
        elif forecasted_precip < 5.0:
            probability = base_prob * 1.0
        elif forecasted_precip < 15.0:
            probability = min(90.0, base_prob * 1.3)
        else:
            probability = min(95.0, base_prob * 1.5)
        
        return min(100.0, max(5.0, probability))