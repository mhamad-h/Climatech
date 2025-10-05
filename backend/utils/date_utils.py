from datetime import datetime, date, timedelta
from typing import List, Tuple, Optional
import calendar


def get_season(date_obj: date) -> str:
    """Get meteorological season for a given date"""
    
    month = date_obj.month
    
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    else:  # [9, 10, 11]
        return "autumn"


def get_season_dates(year: int, season: str) -> Tuple[date, date]:
    """Get start and end dates for a meteorological season"""
    
    season_mapping = {
        "winter": (date(year-1, 12, 1), date(year, 2, 28 if not calendar.isleap(year) else 29)),
        "spring": (date(year, 3, 1), date(year, 5, 31)),
        "summer": (date(year, 6, 1), date(year, 8, 31)),
        "autumn": (date(year, 9, 1), date(year, 11, 30))
    }
    
    if season not in season_mapping:
        raise ValueError(f"Invalid season: {season}")
    
    return season_mapping[season]


def days_between(start_date: date, end_date: date) -> int:
    """Calculate number of days between two dates"""
    return (end_date - start_date).days


def add_months(source_date: date, months: int) -> date:
    """Add months to a date, handling month boundaries correctly"""
    
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    
    # Handle end of month cases
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    
    return date(year, month, day)


def get_month_name(month: int) -> str:
    """Get month name from month number"""
    return calendar.month_name[month]


def get_month_abbreviation(month: int) -> str:
    """Get month abbreviation from month number"""
    return calendar.month_abbr[month]


def is_leap_year(year: int) -> bool:
    """Check if a year is a leap year"""
    return calendar.isleap(year)


def get_days_in_month(year: int, month: int) -> int:
    """Get number of days in a specific month and year"""
    return calendar.monthrange(year, month)[1]


def get_day_of_year(date_obj: date) -> int:
    """Get day of year (1-366)"""
    return date_obj.timetuple().tm_yday


def date_from_day_of_year(year: int, day_of_year: int) -> date:
    """Create date from year and day of year"""
    return date(year, 1, 1) + timedelta(days=day_of_year - 1)


def get_week_of_year(date_obj: date) -> int:
    """Get ISO week number"""
    return date_obj.isocalendar()[1]


def get_quarter(date_obj: date) -> int:
    """Get quarter (1-4) for a date"""
    return (date_obj.month - 1) // 3 + 1


def get_quarter_dates(year: int, quarter: int) -> Tuple[date, date]:
    """Get start and end dates for a quarter"""
    
    if quarter not in [1, 2, 3, 4]:
        raise ValueError("Quarter must be 1, 2, 3, or 4")
    
    start_month = (quarter - 1) * 3 + 1
    end_month = quarter * 3
    
    start_date = date(year, start_month, 1)
    end_date = date(year, end_month, get_days_in_month(year, end_month))
    
    return start_date, end_date


def get_date_range(start_date: date, end_date: date) -> List[date]:
    """Generate list of dates between start and end dates (inclusive)"""
    
    dates = []
    current_date = start_date
    
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=1)
    
    return dates


def get_monthly_dates(start_date: date, months: int) -> List[Tuple[date, date]]:
    """Get list of (start, end) date tuples for each month in the range"""
    
    monthly_ranges = []
    current_date = start_date.replace(day=1)  # Start of month
    
    for _ in range(months):
        end_of_month = date(
            current_date.year, 
            current_date.month, 
            get_days_in_month(current_date.year, current_date.month)
        )
        
        monthly_ranges.append((current_date, end_of_month))
        current_date = add_months(current_date, 1)
    
    return monthly_ranges


def format_date_range(start_date: date, end_date: date) -> str:
    """Format date range as human-readable string"""
    
    if start_date == end_date:
        return start_date.strftime("%B %d, %Y")
    elif start_date.year == end_date.year:
        if start_date.month == end_date.month:
            return f"{start_date.strftime('%B %d')} - {end_date.strftime('%d, %Y')}"
        else:
            return f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"
    else:
        return f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"


def get_season_progress(date_obj: date) -> float:
    """Get progress through current season (0.0 to 1.0)"""
    
    season = get_season(date_obj)
    season_start, season_end = get_season_dates(date_obj.year, season)
    
    # Handle winter spanning years
    if season == "winter" and date_obj.month == 12:
        season_start, season_end = get_season_dates(date_obj.year + 1, season)
    
    total_days = days_between(season_start, season_end)
    elapsed_days = days_between(season_start, date_obj)
    
    return min(1.0, max(0.0, elapsed_days / total_days))


def get_climatological_date_window(
    target_date: date, 
    window_days: int = 30
) -> Tuple[int, int]:
    """Get day-of-year window for climatological analysis"""
    
    target_doy = get_day_of_year(target_date)
    half_window = window_days // 2
    
    start_doy = target_doy - half_window
    end_doy = target_doy + half_window
    
    # Handle year boundaries
    if start_doy < 1:
        start_doy += 365
    if end_doy > 365:
        end_doy -= 365
    
    return start_doy, end_doy


def is_date_in_window(
    test_date: date, 
    target_date: date, 
    window_days: int = 30
) -> bool:
    """Check if test_date falls within climatological window of target_date"""
    
    target_doy = get_day_of_year(target_date)
    test_doy = get_day_of_year(test_date)
    
    # Calculate minimum distance considering year boundary
    distance = min(
        abs(test_doy - target_doy),
        abs(test_doy - target_doy + 365),
        abs(test_doy - target_doy - 365)
    )
    
    return distance <= window_days // 2


def get_forecast_horizon_description(days: int) -> str:
    """Get human-readable description of forecast horizon"""
    
    if days == 1:
        return "Tomorrow"
    elif days <= 7:
        return f"{days} days"
    elif days <= 14:
        return f"{days} days (2 weeks)"
    elif days <= 30:
        return f"{days} days (1 month)"
    elif days <= 60:
        return f"{days} days (2 months)"
    elif days <= 90:
        return f"{days} days (3 months)"
    elif days <= 180:
        return f"{days} days ({days//30} months)"
    else:
        return f"{days} days (extended range)"


def calculate_forecast_decay_factor(days_ahead: int, max_days: int = 180) -> float:
    """Calculate confidence decay factor based on forecast distance"""
    
    if days_ahead <= 1:
        return 1.0
    elif days_ahead <= 7:
        return 1.0 - (days_ahead - 1) * 0.05  # 5% per day for first week
    elif days_ahead <= 30:
        return 0.7 - (days_ahead - 7) * 0.01   # 1% per day for rest of month
    else:
        return max(0.2, 0.47 - (days_ahead - 30) * 0.002)  # 0.2% per day for extended


def get_climate_change_era_years() -> Tuple[int, int]:
    """Get year range for modern climate change era analysis"""
    
    # Modern climate change era generally considered to start around 1980
    current_year = datetime.now().year
    return 1980, current_year


def is_extreme_weather_date(date_obj: date) -> bool:
    """Check if date falls during typical extreme weather seasons"""
    
    month = date_obj.month
    
    # Northern hemisphere extreme weather seasons
    # Hurricane season (June-November), Winter storms (December-March)
    return month in [6, 7, 8, 9, 10, 11, 12, 1, 2, 3]