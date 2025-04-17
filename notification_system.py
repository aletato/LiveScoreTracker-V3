import logging
import platform
import os
from tabulate import tabulate
from typing import Dict

logger = logging.getLogger("score_tracker")

class Notifier:
    """Handles sending notifications when score changes are detected"""
    
    def __init__(self, config):
        self.config = config
        
    def send_notification(self, match: Dict, score_diff: int, 
                         previous_score: Dict, current_score: Dict) -> None:
        """
        Send a notification about score changes
        
        In a real implementation, this could use:
        - Push notifications
        - SMS
        - Email
        - Desktop notifications
        - etc.
        """
        # Get team names with fallbacks
        home_team = match.get('home_name', match.get('home', 'Home Team'))
        away_team = match.get('away_name', match.get('away', 'Away Team'))
        # Try multiple possible field names for league
        league = match.get('league_name', '')
        if not league:
            # Try additional fields that might contain league information
            league = match.get('competition_name', '')
        if not league:
            league = match.get('league', '')
        if not league:
            # Try to extract from event name or description if available
            event_name = match.get('event_name', match.get('description', ''))
            if event_name:
                # Extract league from event name if possible
                # Common patterns: "League Name: Team vs Team" or "Team vs Team - League Name"
                if ':' in event_name:
                    league = event_name.split(':', 1)[0].strip()
                elif ' - ' in event_name:
                    league = event_name.split(' - ', 1)[1].strip()
        
        # If still no league, use a default
        if not league:
            league = "Other Competition"
        # Try multiple possible field names for sport
        sport = match.get('sport_name', match.get('sport', ''))
        if not sport:
            # Try additional fields that might contain sport information
            sport = match.get('category_name', match.get('category', ''))
        if not sport:
            # Check if we can determine sport from league name
            league_lower = league.lower()
            if any(s in league_lower for s in ['soccer', 'football', 'premier', 'la liga', 'bundesliga', 'serie a']):
                sport = 'Soccer'
            elif any(s in league_lower for s in ['nba', 'basketball', 'ncaa']):
                sport = 'Basketball'
            elif any(s in league_lower for s in ['nhl', 'hockey', 'ice']):
                sport = 'Hockey'
            elif any(s in league_lower for s in ['tennis', 'atp', 'wta']):
                sport = 'Tennis'
            elif any(s in league_lower for s in ['baseball', 'mlb']):
                sport = 'Baseball'
            elif any(s in league_lower for s in ['nfl', 'american football']):
                sport = 'American Football'
            else:
                sport = 'Other Sport'  # Better default than "Unknown Sport"
        match_status = match.get('status', 'In Progress')
        
        # Create tabular data for the notification
        table_data = [
            ["⚠️ SCORE UPDATE", f"{score_diff} points scored! ⚠️"],
            ["Sport", sport],
            ["League", league],
            ["Match", f"{home_team} vs {away_team}"],
            ["Previous Score", f"{previous_score['home']}-{previous_score['away']}"],
            ["Current Score", f"{current_score['home']}-{current_score['away']}"],
            ["Status", match_status]
        ]
        
        # Format the table
        message = tabulate(table_data, tablefmt="grid")
        
        # Log notification to console and file
        logger.info("\n" + message)
        
        # Here you could add additional notification methods:
        # self._send_push_notification(message)
        # self._send_email(message)
        # self._send_sms(message)
        
        # Example of how you might implement desktop notifications
        try:
            self._send_desktop_notification(match, score_diff, previous_score, current_score)
        except Exception as e:
            logger.error(f"Failed to send desktop notification: {e}")
    
    def _send_desktop_notification(self, match: Dict, score_diff: int, 
                                  previous_score: Dict, current_score: Dict) -> None:
        """Send a desktop notification (platform-specific implementation)"""
        # This is just an example - you would need to install platform-specific packages
        try:
            # Check platform
            system = platform.system()
            
            # Get team names with fallbacks
            home_team = match.get('home_name', match.get('home', 'Home Team'))
            away_team = match.get('away_name', match.get('away', 'Away Team'))
            # Try multiple possible field names for league
            league = match.get('league_name', '')
            if not league:
                # Try additional fields that might contain league information
                league = match.get('competition_name', '')
            if not league:
                league = match.get('league', '')
            if not league:
                # Try to extract from event name or description if available
                event_name = match.get('event_name', match.get('description', ''))
                if event_name:
                    # Extract league from event name if possible
                    # Common patterns: "League Name: Team vs Team" or "Team vs Team - League Name"
                    if ':' in event_name:
                        league = event_name.split(':', 1)[0].strip()
                    elif ' - ' in event_name:
                        league = event_name.split(' - ', 1)[1].strip()
            
            # If still no league, use a default
            if not league:
                league = "Other Competition"
                
            # Try multiple possible field names for sport
            sport = match.get('sport_name', match.get('sport', ''))
            if not sport:
                # Try additional fields that might contain sport information
                sport = match.get('category_name', match.get('category', ''))
            if not sport:
                # Check if we can determine sport from league name
                league_lower = league.lower()
                if any(s in league_lower for s in ['soccer', 'football', 'premier', 'la liga', 'bundesliga', 'serie a']):
                    sport = 'Soccer'
                elif any(s in league_lower for s in ['nba', 'basketball', 'ncaa']):
                    sport = 'Basketball'
                elif any(s in league_lower for s in ['nhl', 'hockey', 'ice']):
                    sport = 'Hockey'
                elif any(s in league_lower for s in ['tennis', 'atp', 'wta']):
                    sport = 'Tennis'
                elif any(s in league_lower for s in ['baseball', 'mlb']):
                    sport = 'Baseball'
                elif any(s in league_lower for s in ['nfl', 'american football']):
                    sport = 'American Football'
                else:
                    sport = 'Other Sport'  # Better default than "Unknown Sport"
            
            # Create a compact tabulated format for notifications
            table_data = [
                [f"{home_team}", f"{current_score['home']} ({previous_score['home']})"],
                [f"{away_team}", f"{current_score['away']} ({previous_score['away']})"],
            ]
            
            # Format the compact table for notification
            compact_score = tabulate(table_data, tablefmt="simple")
            
            title = f"⚠️ {sport}: {score_diff} points scored! ⚠️"
            message = f"{league}\n{compact_score}"
            
            if system == "Windows":
                # For Windows (requires win10toast package)
                # pip install win10toast
                from win10toast import ToastNotifier
                
                # Remove emojis or replace with safe alternatives for Windows notifications
                # as Windows notifications may have issues with certain Unicode characters
                safe_title = title.encode('ascii', 'replace').decode('ascii')
                safe_message = message.encode('ascii', 'replace').decode('ascii')
                
                # Replace the Unicode replacement character with something more readable
                safe_title = safe_title.replace('?', '!')
                safe_message = safe_message.replace('?', '')
                
                toaster = ToastNotifier()
                toaster.show_toast(safe_title, safe_message, duration=5)
                
            elif system == "Darwin":  # macOS
                # For macOS (requires pync package)
                # pip install pync
                import pync # type: ignore
                pync.notify(message, title=title)
                
            elif system == "Linux":
                # For Linux (requires notify2 package)
                # pip install notify2
                import notify2 # type: ignore
                notify2.init("Score Tracker")
                n = notify2.Notification(title, message)
                n.show()
                
        except ImportError:
            logger.warning(f"Desktop notification packages not available for {platform.system()}")
            # Fall back to console notification only
        except Exception as e:
            logger.error(f"Error sending desktop notification: {e}")
