import datetime
import logging
import pytz
import tzlocal
from typing import Optional, Tuple, Dict

logger = logging.getLogger("score_tracker")

class TimezoneConverter:
    """Handles timezone detection and conversion for match times"""
    
    def __init__(self):
        # Get the local timezone
        try:
            self.local_timezone = tzlocal.get_localzone()
            logger.info(f"Detected local timezone: {self.local_timezone}")
        except Exception as e:
            logger.error(f"Failed to detect local timezone: {e}")
            # Default to UTC if detection fails
            self.local_timezone = pytz.UTC
            logger.info("Using UTC as fallback timezone")
        
        # Assume API uses UTC timezone (most common for sports APIs)
        self.api_timezone = pytz.UTC
    
    def get_local_timezone_name(self) -> str:
        """Get the name of the local timezone"""
        return str(self.local_timezone)
    
    def get_local_timezone_offset(self) -> str:
        """Get the offset of the local timezone from UTC"""
        now = datetime.datetime.now(self.local_timezone)
        return now.strftime("%z")
    
    def convert_time(self, time_str: str, date_str: Optional[str] = None) -> str:
        """
        Convert a time string from API timezone to local timezone
        
        Args:
            time_str: Time string from API (e.g., "15:30")
            date_str: Optional date string (e.g., "2023-04-17")
            
        Returns:
            Converted time string in local timezone
        """
        try:
            # Handle empty or invalid time strings
            if not time_str or time_str.lower() in ["tbd", "?"]:
                return time_str
            
            # Try to parse the time string
            # Handle different possible formats
            dt = None
            
            # If we have both date and time
            if date_str:
                try:
                    # Try ISO format first (YYYY-MM-DD)
                    if "-" in date_str:
                        # Try with different time formats
                        for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"]:
                            try:
                                dt = datetime.datetime.strptime(f"{date_str} {time_str}", fmt)
                                break
                            except ValueError:
                                continue
                    
                    # Try DD/MM/YYYY format
                    if not dt and "/" in date_str:
                        for fmt in ["%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S"]:
                            try:
                                dt = datetime.datetime.strptime(f"{date_str} {time_str}", fmt)
                                break
                            except ValueError:
                                continue
                    
                    # Try MM/DD/YYYY format
                    if not dt and "/" in date_str:
                        for fmt in ["%m/%d/%Y %H:%M", "%m/%d/%Y %H:%M:%S"]:
                            try:
                                dt = datetime.datetime.strptime(f"{date_str} {time_str}", fmt)
                                break
                            except ValueError:
                                continue
                except Exception as e:
                    logger.warning(f"Error parsing date '{date_str}': {e}")
            
            # If we couldn't parse with date or don't have a date, try just the time
            if not dt:
                # Try to parse just the time
                try:
                    # Get today's date
                    today = datetime.datetime.now().date()
                    
                    # Try different time formats
                    for fmt in ["%H:%M", "%H:%M:%S"]:
                        try:
                            time_obj = datetime.datetime.strptime(time_str, fmt).time()
                            dt = datetime.datetime.combine(today, time_obj)
                            break
                        except ValueError:
                            continue
                    
                    if not dt:
                        # If all parsing attempts failed, return the original string
                        return time_str
                        
                except Exception as e:
                    logger.warning(f"Error parsing time '{time_str}': {e}")
                    return time_str
            
            # Localize the datetime to the API timezone
            dt_with_tz = self.api_timezone.localize(dt)
            
            # Convert to local timezone
            local_dt = dt_with_tz.astimezone(self.local_timezone)
            
            # Format the time for display without timezone indicator
            local_time = local_dt.strftime("%H:%M")
            
            # Return just the time without timezone offset
            return f"{local_time}"
            
        except Exception as e:
            logger.error(f"Error converting time '{time_str}': {e}")
            return time_str  # Return original if conversion fails
    
    def convert_date_time(self, date_str: str, time_str: str) -> Tuple[str, str]:
        """
        Convert a date and time from API timezone to local timezone
        
        Args:
            date_str: Date string from API (e.g., "2023-04-17")
            time_str: Time string from API (e.g., "15:30")
            
        Returns:
            Tuple of (converted_date, converted_time) in local timezone
        """
        try:
            # Handle empty or invalid strings
            if not date_str or not time_str or time_str.lower() in ["tbd", "?"]:
                return date_str, time_str
            
            # Try to parse the date and time
            dt = None
            
            # Try ISO format first (YYYY-MM-DD)
            if "-" in date_str:
                try:
                    dt = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                except ValueError:
                    try:
                        dt = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass
            
            # Try DD/MM/YYYY format
            if not dt and "/" in date_str:
                try:
                    dt = datetime.datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M")
                except ValueError:
                    try:
                        dt = datetime.datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M:%S")
                    except ValueError:
                        pass
            
            # Try MM/DD/YYYY format
            if not dt and "/" in date_str:
                try:
                    dt = datetime.datetime.strptime(f"{date_str} {time_str}", "%m/%d/%Y %H:%M")
                except ValueError:
                    try:
                        dt = datetime.datetime.strptime(f"{date_str} {time_str}", "%m/%d/%Y %H:%M:%S")
                    except ValueError:
                        pass
            
            if not dt:
                # If parsing failed, return the originals
                return date_str, time_str
            
            # Localize the datetime to the API timezone
            dt_with_tz = self.api_timezone.localize(dt)
            
            # Convert to local timezone
            local_dt = dt_with_tz.astimezone(self.local_timezone)
            
            # Format the date and time for display
            local_date = local_dt.strftime("%Y-%m-%d")
            local_time = local_dt.strftime("%H:%M")
            
            # Check if the date changed during conversion
            if local_date != date_str:
                # If date changed, include both date and time without timezone
                return local_date, f"{local_time}"
            else:
                # If date didn't change, just include time without timezone
                return date_str, f"{local_time}"
            
        except Exception as e:
            logger.error(f"Error converting date '{date_str}' and time '{time_str}': {e}")
            return date_str, time_str  # Return originals if conversion fails
