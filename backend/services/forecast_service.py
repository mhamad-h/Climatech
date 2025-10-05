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
            precipitation = (weight_persistence * persistence_result["precipitation"] + 
                           weight_analog * analog_result["precipitation"])
            humidity = (weight_persistence * persistence_result["humidity"] + 
                       weight_analog * analog_result["humidity"])
            wind_speed = (weight_persistence * persistence_result["wind_speed"] + 
                         weight_analog * analog_result["wind_speed"])
            
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
                precipitation = climate_normal.precipitation_normal
                humidity = climate_normal.humidity_normal
                wind_speed = climate_normal.wind_speed_normal
                
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
                    wind_speed = np.mean([d.wind_speed for d in month_data])
                else:
                    # Last resort: use overall averages
                    temp_max = np.mean([d.temperature_max for d in historical_data])
                    temp_min = np.mean([d.temperature_min for d in historical_data])
                    precipitation = np.mean([d.precipitation for d in historical_data])
                    humidity = np.mean([d.humidity for d in historical_data])
                    wind_speed = np.mean([d.wind_speed for d in historical_data])
                
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
        data_quality_score = 85.0  # Assume good quality NASA data
        
        temp_confidence = self.climatology_service.calculate_confidence_level(
            "climatology", days_ahead, data_quality_score, method_confidence
        )
        precip_confidence = self.climatology_service.calculate_confidence_level(
            "climatology", days_ahead, data_quality_score, method_confidence * 0.8  # Lower for precipitation
        )
        
        # Calculate precipitation probability
        precip_probability = min(100.0, max(0.0, precipitation * 10))  # Simple heuristic
        
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