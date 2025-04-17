"""
Live Match Score Tracker Bot
----------------------------
This bot tracks live matches from live-score-api and sends notifications
when 2 or more points are scored in a match.

Features:
- Track specific matches by team name, league, or match ID
- Real-time notifications for score changes
- Configurable notification threshold
- Resilient error handling and retry logic

Requirements:
- Python 3.9+
- Requests library
- A valid API key for live-score-api
- Tabulate library for formatted output
- win10toast (for Windows notifications)
- pync (for macOS notifications)
- notify2 (for Linux notifications)


"""

import requests
import time
import logging
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Set, Tuple
from dataclasses import dataclass, field
import threading
import concurrent.futures
from tabulate import tabulate

# Configure logging
# Import io and sys for UTF-8 stream handling
import io
import sys

# Configure console encoding for Windows
if os.name == 'nt':
    # Force UTF-8 encoding for stdout
    sys.stdout.reconfigure(encoding='utf-8')
    # Set console code page to UTF-8
    os.system('chcp 65001 > nul')

# Create handlers with UTF-8 encoding
file_handler = logging.FileHandler("score_tracker.log", encoding='utf-8')

# Create a StreamHandler that writes to stdout with UTF-8 encoding
stream_handler = logging.StreamHandler(sys.stdout)

# Configure formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

# Configure root logger
logging.basicConfig(level=logging.INFO, handlers=[file_handler, stream_handler])
logger = logging.getLogger("score_tracker")

# Configuration
@dataclass
class Config:
    api_key: str
    api_secret: str
    notification_threshold: int = 2  # Notify when this many points are scored
    polling_interval: float = 10.0  # Seconds between API calls
    sports: List[str] = None  # None means all sports
    tracked_teams: List[str] = field(default_factory=list)  # Teams to track (case insensitive)
    tracked_leagues: List[str] = field(default_factory=list)  # Leagues to track (case insensitive)
    tracked_match_ids: List[str] = field(default_factory=list)  # Specific match IDs to track
    exclude_teams: List[str] = field(default_factory=list)  # Teams to exclude (case insensitive)
    exclude_leagues: List[str] = field(default_factory=list)  # Leagues to exclude (case insensitive)
    track_all_matches: bool = True  # If False, only track matches that match inclusion criteria
    max_concurrent_requests: int = 5
    max_retries: int = 3
    retry_delay: float = 2.0  # Seconds
    cache_expiry: int = 60  # Seconds
    debug_mode: bool = False  # Print additional debug information


class ScoreCache:
    """Cache for storing and managing match scores"""
    
    def __init__(self, expiry_seconds: int = 60):
        self._cache: Dict[str, Dict] = {}
        self._expiry_seconds = expiry_seconds
        self._lock = threading.RLock()
    
    def get(self, match_id: str) -> Optional[Dict]:
        """Get a match from cache if it exists and isn't expired"""
        with self._lock:
            if match_id not in self._cache:
                return None
            
            entry = self._cache[match_id]
            if time.time() - entry["timestamp"] > self._expiry_seconds:
                # Entry expired
                del self._cache[match_id]
                return None
                
            return entry["data"]
    
    def set(self, match_id: str, data: Dict) -> None:
        """Store match data in cache"""
        with self._lock:
            self._cache[match_id] = {
                "data": data,
                "timestamp": time.time()
            }
    
    def clear_expired(self) -> None:
        """Remove all expired entries from cache"""
        with self._lock:
            now = time.time()
            expired_keys = [
                k for k, v in self._cache.items() 
                if now - v["timestamp"] > self._expiry_seconds
            ]
            
            for key in expired_keys:
                del self._cache[key]


class Notifier:
    """Handles sending notifications when score changes are detected"""
    
    def __init__(self, config: Config):
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
        league = match.get('league_name', match.get('competition_name', 'Unknown League'))
        sport = match.get('sport_name', match.get('sport', 'Unknown Sport'))
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
            import platform
            system = platform.system()
            
            # Get team names with fallbacks
            home_team = match.get('home_name', match.get('home', 'Home Team'))
            away_team = match.get('away_name', match.get('away', 'Away Team'))
            sport = match.get('sport_name', match.get('sport', 'Unknown Sport'))
            league = match.get('league_name', match.get('competition_name', 'Unknown League'))
            
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


class LiveScoreAPI:
    """Handles interactions with the live-score-api"""
    
    def __init__(self, config: Config):
        self.config = config
        self.base_url = "https://livescore-api.com/api-client"
        self.session = requests.Session()
        # Add retry mechanism 
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=config.max_concurrent_requests
        )
        # Keep track of scheduled matches
        self.scheduled_matches = []
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Make a request to the API with retry mechanism
        
        Args:
            endpoint: The API endpoint (without base URL)
            params: Additional query parameters
            
        Returns:
            The JSON response as a dictionary
            
        Raises:
            Exception: If the request fails after all retries
        """
        if params is None:
            params = {}
            
        # Add API credentials to all requests
        params.update({
            "key": self.config.api_key,
            "secret": self.config.api_secret
        })
        
        url = f"{self.base_url}/{endpoint}"
        
        if self.config.debug_mode:
            logger.info(f"Making API request to: {endpoint} with params: {params}")
        
        last_exception = None
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.get(url, params=params, timeout=30)
                
                if self.config.debug_mode:
                    logger.info(f"Response status: {response.status_code}")
                    logger.info(f"Response content: {response.text[:500]}...")
                
                response.raise_for_status()
                
                data = response.json()
                if data.get("success") is False:
                    error_msg = data.get("error", "Unknown API error")
                    raise Exception(f"API error: {error_msg}")
                    
                return data
                
            except requests.RequestException as e:
                last_exception = e
                logger.warning(f"Request failed (attempt {attempt+1}/{self.config.max_retries}): {e}")
                time.sleep(self.config.retry_delay * (2 ** attempt))  # Exponential backoff
            except Exception as e:
                last_exception = e
                logger.warning(f"Error processing response (attempt {attempt+1}/{self.config.max_retries}): {e}")
                time.sleep(self.config.retry_delay * (2 ** attempt))
        
        # If we get here, all retries failed
        error_msg = f"Failed to make API request after {self.config.max_retries} attempts"
        logger.error(error_msg)
        raise Exception(error_msg) from last_exception
    
    def get_live_matches(self) -> List[Dict]:
        """Get all currently live matches"""
        try:
            params = {}
            
            # Add sport filter if specific sports are configured
            if self.config.sports is not None and len(self.config.sports) == 1:
                # If only one sport is configured, we can use the API's sport filter
                params["sport"] = self.config.sports[0]
                if self.config.debug_mode:
                    logger.info(f"Filtering API request for sport: {self.config.sports[0]}")
            
            response = self._make_request("scores/live.json", params)
            
            # Check for different possible response structures
            if "data" in response:
                if "match" in response["data"]:
                    return response["data"]["match"]
                elif "matches" in response["data"]:
                    return response["data"]["matches"]
                elif "fixtures" in response["data"]:
                    return response["data"]["fixtures"]
            
            logger.warning(f"Unexpected API response format: {response}")
            return []
            
        except Exception as e:
            logger.error(f"Error fetching live matches: {e}")
            return []
    
    def get_scheduled_matches(self) -> List[Dict]:
        """Get upcoming scheduled matches"""
        try:
            params = {}
            
            # Add sport filter if specific sports are configured
            if self.config.sports is not None:
                # If we have specific sports, we need to make separate requests for each
                all_matches = []
                for sport in self.config.sports:
                    sport_params = params.copy()
                    sport_params["sport"] = sport
                    if self.config.debug_mode:
                        logger.info(f"Fetching scheduled matches for sport: {sport}")
                    
                    response = self._make_request("fixtures/matches.json", sport_params)
                    
                    # Extract matches from response
                    if "data" in response:
                        if "fixtures" in response["data"]:
                            all_matches.extend(response["data"]["fixtures"])
                        elif "matches" in response["data"]:
                            all_matches.extend(response["data"]["matches"])
                
                # Store scheduled matches for later use
                self.scheduled_matches = all_matches
                return all_matches
            else:
                # If no specific sports, get all scheduled matches
                response = self._make_request("fixtures/matches.json", params)
                
                # Check for different possible response structures
                if "data" in response:
                    if "fixtures" in response["data"]:
                        self.scheduled_matches = response["data"]["fixtures"]
                        return response["data"]["fixtures"]
                    elif "matches" in response["data"]:
                        self.scheduled_matches = response["data"]["matches"]
                        return response["data"]["matches"]
                
                logger.warning(f"Unexpected API response format for scheduled matches: {response}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching scheduled matches: {e}")
            return []
    
    def get_match_score(self, match_id: str) -> Dict:
        """Get detailed score for a specific match"""
        try:
            # Instead of using the id parameter which seems to return all matches,
            # we'll get all live matches and filter for the specific match ID
            response = self._make_request("scores/live.json")
            
            # Handle different possible response structures
            if "data" in response and "match" in response["data"]:
                matches = response["data"]["match"]
                if isinstance(matches, list):
                    # Find the match with the matching ID
                    for match in matches:
                        if str(match.get("id")) == str(match_id):
                            return match
                    
                    # If we get here, we didn't find the match
                    logger.warning(f"Match ID {match_id} not found in live matches")
                    return {}
                elif isinstance(matches, dict) and str(matches.get("id")) == str(match_id):
                    return matches
            
            logger.warning(f"Unexpected API response format for match {match_id}: {response}")
            return {}
            
        except Exception as e:
            logger.error(f"Error fetching match score for {match_id}: {e}")
            return {}
    
    def get_match_scores_parallel(self, match_ids: List[str]) -> Dict[str, Dict]:
        """Get scores for multiple matches in parallel"""
        def get_single_match(match_id):
            try:
                return match_id, self.get_match_score(match_id)
            except Exception as e:
                logger.error(f"Error fetching match {match_id}: {e}")
                return match_id, {}
                
        results = {}
        futures = [self.executor.submit(get_single_match, match_id) for match_id in match_ids]
        
        for future in concurrent.futures.as_completed(futures):
            try:
                match_id, match_data = future.result()
                if match_data:  # Only add if we got data
                    results[match_id] = match_data
            except Exception as e:
                logger.error(f"Error processing match result: {e}")
                
        return results


class MatchFilter:
    """Filters matches based on configuration"""
    
    def __init__(self, config: Config):
        self.config = config
        # Convert lists to sets and lowercase for case-insensitive matching
        self.tracked_teams = {team.lower() for team in config.tracked_teams}
        self.tracked_leagues = {league.lower() for league in config.tracked_leagues}
        self.tracked_match_ids = set(config.tracked_match_ids)
        self.exclude_teams = {team.lower() for team in config.exclude_teams}
        self.exclude_leagues = {league.lower() for league in config.exclude_leagues}
        
        # Convert sports to lowercase set for case-insensitive matching
        self.tracked_sports = None
        if config.sports is not None:
            self.tracked_sports = {sport.lower() for sport in config.sports}
        
        # Keep track of matches we're filtering
        self.filtered_matches: Set[str] = set()
        self.tracked_matches_info: Dict[str, Dict] = {}
    
    def _is_team_match(self, match: Dict) -> bool:
        """Check if match involves a tracked team"""
        home = match.get('home_name', match.get('home', '')).lower()
        away = match.get('away_name', match.get('away', '')).lower()
        
        # Check if either team is in the tracked teams list
        for team in self.tracked_teams:
            if team in home or team in away:
                return True
        
        return False
    
    def _is_league_match(self, match: Dict) -> bool:
        """Check if match is in a tracked league"""
        league = match.get('league_name', match.get('competition_name', '')).lower()
        
        # Check if the league is in the tracked leagues list
        for tracked_league in self.tracked_leagues:
            if tracked_league in league:
                return True
                
        return False
    
    def _is_excluded_team(self, match: Dict) -> bool:
        """Check if match involves an excluded team"""
        if not self.exclude_teams:
            return False
            
        home = match.get('home_name', match.get('home', '')).lower()
        away = match.get('away_name', match.get('away', '')).lower()
        
        # Check if either team is in the excluded teams list
        for team in self.exclude_teams:
            if team in home or team in away:
                return True
                
        return False
    
    def _is_excluded_league(self, match: Dict) -> bool:
        """Check if match is in an excluded league"""
        if not self.exclude_leagues:
            return False
            
        league = match.get('league_name', match.get('competition_name', '')).lower()
        
        # Check if the league is in the excluded leagues list
        for excluded_league in self.exclude_leagues:
            if excluded_league in league:
                return True
                
        return False
    
    def _is_tracked_sport(self, match: Dict) -> bool:
        """Check if match is for a tracked sport"""
        # If no specific sports are tracked, track all sports
        if self.tracked_sports is None:
            return True
            
        # Get the sport from the match data
        sport = match.get('sport_name', match.get('sport', '')).lower()
        
        # Check if the sport is in the tracked sports list
        return sport in self.tracked_sports
    
    def should_track_match(self, match: Dict) -> bool:
        """Determine if this match should be tracked based on configuration"""
        match_id = str(match.get('id', ''))
        
        # First, check if this match is for a tracked sport
        if not self._is_tracked_sport(match):
            return False
        
        # Next, check if this match is explicitly tracked by ID
        if match_id in self.tracked_match_ids:
            if match_id not in self.tracked_matches_info:
                home = match.get('home_name', match.get('home', 'Unknown'))
                away = match.get('away_name', match.get('away', 'Unknown'))
                league = match.get('league_name', match.get('competition_name', 'Unknown League'))
                sport = match.get('sport_name', match.get('sport', 'Unknown Sport'))
                # Extract match time if available
                match_time = match.get('time', match.get('match_time', ''))
                # Extract score if available
                score = match.get('score', '0-0')
                
                # Create tabular data for the specific match info
                table_data = [
                    ["Match ID", match_id],
                    ["Teams", f"{home} vs {away}"],
                    ["Sport", sport],
                    ["League", league],
                    ["Time", match_time],
                    ["Score", score],
                    ["Tracking Reason", "Explicitly tracked by ID"]
                ]
                
                # Format the table
                table = tabulate(table_data, tablefmt="grid")
                
                # Log the specific match tracking info
                logger.info(f"\nTracking specific match by ID:\n{table}")
                
                self.tracked_matches_info[match_id] = {
                    'home': home,
                    'away': away,
                    'league': league,
                    'sport': sport
                }
            return True
        
        # Then check exclusion criteria - these override inclusion
        if self._is_excluded_team(match) or self._is_excluded_league(match):
            return False
        
        # If we're tracking all matches that aren't excluded, return True
        if self.config.track_all_matches:
            return True
        
        # Otherwise, only track matches that meet inclusion criteria
        if self._is_team_match(match) or self._is_league_match(match):
            return True
            
        # If we get here, we're not tracking this match
        return False
    
    def log_filtering_info(self, match: Dict) -> None:
        """Log information about whether a match is being tracked"""
        match_id = str(match.get('id', ''))
        
        # Skip if we've already logged this match
        if match_id in self.filtered_matches:
            return
            
        # Add to set of filtered matches
        self.filtered_matches.add(match_id)
        
        # Get match info
        home = match.get('home_name', match.get('home', 'Unknown'))
        away = match.get('away_name', match.get('away', 'Unknown'))
        league = match.get('league_name', match.get('competition_name', 'Unknown League'))
        sport = match.get('sport_name', match.get('sport', 'Unknown Sport'))
        
        # Extract match time if available
        match_time = match.get('time', match.get('match_time', ''))
        
        # Extract score if available
        score = match.get('score', '0-0')
        
        # Create tabular data for the match info
        table_data = [
            ["Match ID", match_id],
            ["Teams", f"{home} vs {away}"],
            ["Sport", sport],
            ["League", league],
            ["Time", match_time],
            ["Score", score],
            ["Status", "Tracking" if self.should_track_match(match) else "Not Tracking"]
        ]
        
        # If not tracking and in debug mode, add reason
        if not self.should_track_match(match) and self.config.debug_mode:
            reason = "Not in tracked sports" if not self._is_tracked_sport(match) else "Excluded or not matching criteria"
            table_data.append(["Reason", reason])
        
        # Format the table
        table = tabulate(table_data, tablefmt="grid")
        
        # Log whether we're tracking this match
        if self.should_track_match(match):
            logger.info(f"\nTracking new match:\n{table}")
        else:
            if self.config.debug_mode:
                logger.info(f"\nNot tracking match:\n{table}")


class ScoreTracker:
    """Main class that manages tracking score changes"""
    
    def __init__(self, config: Config):
        self.config = config
        self.api = LiveScoreAPI(config)
        self.notifier = Notifier(config)
        self.score_cache = ScoreCache(expiry_seconds=config.cache_expiry)
        self.match_filter = MatchFilter(config)
        self.running = False
        self.track_thread = None
        
        # Store last known scores for each match
        self.last_scores: Dict[str, Dict] = {}
    
    def extract_score(self, match_data: Dict) -> Dict:
        """Extract home and away scores from match data"""
        try:
            # Debug the match data if enabled
            if self.config.debug_mode:
                logger.info(f"Extracting score from match data: {json.dumps(match_data)}")
                
            # Handle different possible score formats
            score = match_data.get("score", "0-0")
            
            # First try direct score field
            if isinstance(score, str) and "-" in score:
                parts = score.split("-")
                
                # Handle special score formats like "? - ?" or "TBD - TBD"
                try:
                    home_score = int(parts[0].strip())
                except ValueError:
                    home_score = 0  # Default to 0 if score can't be parsed
                    
                try:
                    away_score = int(parts[1].strip())
                except ValueError:
                    away_score = 0  # Default to 0 if score can't be parsed
                    
                return {
                    "home": home_score,
                    "away": away_score
                }
            # Fallback to separate score fields if available
            elif "fs_home" in match_data and "fs_away" in match_data:
                try:
                    home_score = int(str(match_data.get("fs_home", 0)).strip() or 0)
                except ValueError:
                    home_score = 0
                    
                try:
                    away_score = int(str(match_data.get("fs_away", 0)).strip() or 0)
                except ValueError:
                    away_score = 0
                    
                return {
                    "home": home_score,
                    "away": away_score
                }
            # Another possible format in the API
            elif "home_score" in match_data and "away_score" in match_data:
                try:
                    home_score = int(str(match_data.get("home_score", 0)).strip() or 0)
                except ValueError:
                    home_score = 0
                    
                try:
                    away_score = int(str(match_data.get("away_score", 0)).strip() or 0)
                except ValueError:
                    away_score = 0
                    
                return {
                    "home": home_score,
                    "away": away_score
                }
            # Yet another format with scores object
            elif "scores" in match_data:
                scores = match_data["scores"]
                if isinstance(scores, dict):
                    try:
                        home_score = int(str(scores.get("home_score", 0)).strip() or 0)
                    except ValueError:
                        home_score = 0
                        
                    try:
                        away_score = int(str(scores.get("away_score", 0)).strip() or 0)
                    except ValueError:
                        away_score = 0
                        
                    return {
                        "home": home_score,
                        "away": away_score
                    }
            
            # If none of the above worked, return default 0-0
            if self.config.debug_mode:
                logger.warning(f"Could not find score in expected format, using default 0-0: {match_data}")
            return {"home": 0, "away": 0}
            
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing score '{match_data.get('score')}': {e}")
            return {"home": 0, "away": 0}

    
    def calculate_score_diff(self, prev_score: Dict, curr_score: Dict) -> int:
        """Calculate total number of points scored since last check"""
        prev_total = prev_score["home"] + prev_score["away"]
        curr_total = curr_score["home"] + curr_score["away"]
        return curr_total - prev_total
    
    def process_match(self, match_id: str, match_data: Dict) -> None:
        """Process a single match and check for score changes"""
        # Check if we should track this match
        if not self.match_filter.should_track_match(match_data):
            return
            
        # Log filtering info if this is a new match
        self.match_filter.log_filtering_info(match_data)
        
        current_score = self.extract_score(match_data)
        
        # Check if we have previous score data
        if match_id in self.last_scores:
            previous_score = self.last_scores[match_id]
            score_diff = self.calculate_score_diff(previous_score, current_score)
            
            # Check if score difference meets or exceeds threshold
            if score_diff >= self.config.notification_threshold:
                self.notifier.send_notification(
                    match_data, 
                    score_diff, 
                    previous_score, 
                    current_score
                )
        else:
            # First time seeing this match, log it
            if self.config.debug_mode:
                home_team = match_data.get('home_name', match_data.get('home', 'Home Team'))
                away_team = match_data.get('away_name', match_data.get('away', 'Away Team'))
                sport = match_data.get('sport_name', match_data.get('sport', 'Unknown Sport'))
                # Extract match time if available
                match_time = match_data.get('time', match_data.get('match_time', ''))
                logger.info(f"Started tracking match: {home_team} vs {away_team}, Sport: {sport}, Initial score: {current_score['home']}-{current_score['away']} (Time: {match_time})")
        
        # Update last known score
        self.last_scores[match_id] = current_score
    
    def display_scheduled_matches(self, matches: List[Dict]) -> None:
        """Display information about scheduled matches using tabulate"""
        if not matches:
            logger.info("No scheduled matches found.")
            return
            
        # Filter matches by tracked sports if configured
        filtered_matches = []
        if self.config.sports is not None:
            tracked_sports = {sport.lower() for sport in self.config.sports}
            for match in matches:
                sport = match.get('sport_name', match.get('sport', '')).lower()
                if sport in tracked_sports:
                    filtered_matches.append(match)
        else:
            filtered_matches = matches
            
        if not filtered_matches:
            logger.info("No scheduled matches found for your tracked sports.")
            return
            
        # Sort matches by start time
        try:
            filtered_matches.sort(key=lambda m: m.get('time', m.get('scheduled', '00:00')))
        except Exception:
            # If sorting fails, just use the original order
            pass
            
        # Prepare data for tabulate
        table_data = []
        for i, match in enumerate(filtered_matches[:10], 1):  # Show first 10 matches
            home_team = match.get('home_name', match.get('home', 'Home Team'))
            away_team = match.get('away_name', match.get('away', 'Away Team'))
            league = match.get('league_name', match.get('competition_name', 'Unknown League'))
            sport = match.get('sport_name', match.get('sport', 'Unknown Sport'))
            
            # Extract match time if available
            match_time = match.get('time', match.get('scheduled', 'Time unknown'))
            match_date = match.get('date', 'Today')
            
            table_data.append([
                i,
                sport,
                f"{home_team} vs {away_team}",
                league,
                f"{match_date} at {match_time}"
            ])
        
        # Create table with tabulate
        headers = ["#", "Sport", "Match", "League", "Scheduled Time"]
        table = tabulate(table_data, headers=headers, tablefmt="grid")
        
        # Display scheduled matches
        logger.info("\n===== SCHEDULED MATCHES =====")
        logger.info(f"Found {len(filtered_matches)} upcoming matches for your tracked sports:")
        logger.info("\n" + table)
            
        if len(filtered_matches) > 10:
            logger.info(f"... and {len(filtered_matches) - 10} more matches")
            
        logger.info("=============================")
    
    def track_matches(self) -> None:
        """Main loop to track live matches and their scores"""
        logger.info("Starting match tracking...")
        
        while self.running:
            try:
                # Get all live matches
                live_matches = self.api.get_live_matches()
                match_count = len(live_matches)
                logger.info(f"Found {match_count} live matches")
                
                if match_count > 0:
                    # Get match IDs - handle different possible structures
                    match_ids = []
                    for match in live_matches:
                        if isinstance(match, dict) and 'id' in match:
                            match_ids.append(match['id'])
                    
                    # If we found no valid match IDs, use the live matches directly
                    if not match_ids and match_count > 0:
                        for match in live_matches:
                            if self.config.debug_mode:
                                logger.info(f"Processing match directly: {match}")
                            self.process_match(str(match.get('id', 'unknown')), match)
                    else:
                        # We have IDs, get detailed scores in parallel
                        if self.config.debug_mode:
                            logger.info(f"Getting details for {len(match_ids)} matches: {match_ids}")
                        
                        # Handle smaller batches to avoid overwhelming the API
                        for i in range(0, len(match_ids), self.config.max_concurrent_requests):
                            batch = match_ids[i:i+self.config.max_concurrent_requests]
                            
                            # For small API limits, process one at a time to be safe
                            for match_id in batch:
                                try:
                                    match_data = self.api.get_match_score(match_id)
                                    if match_data:  # Skip empty results
                                        self.process_match(match_id, match_data)
                                except Exception as e:
                                    logger.error(f"Error processing match {match_id}: {e}")
                else:
                    # No live matches found, check for scheduled matches
                    logger.warning("No live matches found for your tracked sports.")
                    scheduled_matches = self.api.get_scheduled_matches()
                    if scheduled_matches:
                        self.display_scheduled_matches(scheduled_matches)
                    else:
                        logger.info("No scheduled matches found either. Will check again later.")
                
                # Display a summary of all live matches
                self.display_match_status_summary(live_matches)
                
                # Cleanup expired cache entries
                self.score_cache.clear_expired()
                
            except Exception as e:
                logger.error(f"Error in tracking loop: {e}")
            
            # Wait for next polling interval
            time.sleep(self.config.polling_interval)
    
    def start(self):
        """Start the score tracker in a separate thread"""
        if self.running:
            logger.warning("Score tracker is already running")
            return
            
        self.running = True
        self.track_thread = threading.Thread(target=self.track_matches)
        self.track_thread.daemon = True
        self.track_thread.start()
        logger.info("Score tracker started in background")
    
    def stop(self):
        """Stop the score tracker"""
        logger.info("Stopping score tracker...")
        self.running = False
        
        if self.track_thread and self.track_thread.is_alive():
            self.track_thread.join(timeout=5.0)
            
        logger.info("Score tracker stopped")

    def display_match_comparison(self, match_data: Dict, previous_scores: Dict[str, Dict], current_scores: Dict[str, Dict]) -> None:
        """
        Display a comparison table for multiple matches, showing score changes
        
        Args:
            match_data: Dictionary mapping match IDs to match information
            previous_scores: Dictionary mapping match IDs to previous scores
            current_scores: Dictionary mapping match IDs to current scores
        """
        if not match_data or not previous_scores or not current_scores:
            logger.info("No match comparison data available.")
            return
            
        # Prepare data for tabulate
        table_data = []
        headers = ["Match ID", "Teams", "League", "Previous", "Current", "Change"]
        
        for match_id, match in match_data.items():
            if match_id not in previous_scores or match_id not in current_scores:
                continue
                
            home_team = match.get('home_name', match.get('home', 'Home Team'))
            away_team = match.get('away_name', match.get('away', 'Away Team'))
            teams = f"{home_team} vs {away_team}"
            
            league = match.get('league_name', match.get('competition_name', 'Unknown League'))
            
            prev = previous_scores.get(match_id, {"home": 0, "away": 0})
            curr = current_scores.get(match_id, {"home": 0, "away": 0})
            
            prev_score = f"{prev['home']}-{prev['away']}"
            curr_score = f"{curr['home']}-{curr['away']}"
            
            # Calculate score difference
            prev_total = prev['home'] + prev['away']
            curr_total = curr['home'] + curr['away']
            diff = curr_total - prev_total
            
            # Use color or symbols to indicate change
            if diff > 0:
                change = f"+{diff} ⬆️"
            elif diff < 0:
                change = f"{diff} ⬇️"
            else:
                change = "0 ↔️"
                
            table_data.append([
                match_id,
                teams,
                league,
                prev_score,
                curr_score,
                change
            ])
        
        # Sort by score change (descending)
        table_data.sort(key=lambda x: int(x[5].split()[0].replace('+', '')), reverse=True)
        
        # Create and display the table
        if table_data:
            table = tabulate(table_data, headers=headers, tablefmt="grid")
            logger.info("\n===== MATCH SCORE COMPARISON =====")
            logger.info("\n" + table)
            logger.info("=================================")
        else:
            logger.info("No score changes to display.")

    def display_summary_statistics(self) -> None:
        """Display summary statistics of tracked matches using tabulate"""
        if not self.last_scores:
            logger.info("No match data available for statistics.")
            return
        
        # Collect match statistics
        match_stats = []
        
        for match_id, current_score in self.last_scores.items():
            # Get match from tracked info if available, otherwise create a placeholder
            match_info = self.match_filter.tracked_matches_info.get(match_id, {})
            
            if not match_info:
                # Match not in tracked_matches_info, need to find it from elsewhere
                # This is a placeholder entry that will be updated if we have more info
                match_info = {
                    'home': f"Team {match_id} (H)",
                    'away': f"Team {match_id} (A)",
                    'league': "Unknown League",
                    'sport': "Unknown Sport"
                }
            
            # Calculate total score
            total_score = current_score['home'] + current_score['away']
            
            # Add to stats list
            match_stats.append({
                'match_id': match_id,
                'home': match_info['home'],
                'away': match_info['away'],
                'league': match_info['league'],
                'sport': match_info['sport'],
                'home_score': current_score['home'],
                'away_score': current_score['away'],
                'total_score': total_score
            })
        
        # Sort by total score (descending)
        match_stats.sort(key=lambda x: x['total_score'], reverse=True)
        
        # Prepare data for tabulate
        table_data = []
        for stat in match_stats[:10]:  # Show top 10 matches by score
            table_data.append([
                stat['match_id'],
                f"{stat['home']} vs {stat['away']}",
                stat['sport'],
                stat['league'],
                f"{stat['home_score']}-{stat['away_score']}",
                stat['total_score']
            ])
        
        # Create and display the table
        headers = ["Match ID", "Teams", "Sport", "League", "Score", "Total Points"]
        
        if table_data:
            table = tabulate(table_data, headers=headers, tablefmt="grid")
            
            # Group statistics by sport
            sport_stats = {}
            for stat in match_stats:
                sport = stat['sport']
                if sport not in sport_stats:
                    sport_stats[sport] = {
                        'count': 0,
                        'total_points': 0,
                        'avg_points': 0
                    }
                
                sport_stats[sport]['count'] += 1
                sport_stats[sport]['total_points'] += stat['total_score']
            
            # Calculate averages
            for sport in sport_stats:
                if sport_stats[sport]['count'] > 0:
                    sport_stats[sport]['avg_points'] = round(
                        sport_stats[sport]['total_points'] / sport_stats[sport]['count'], 1
                    )
            
            # Create sport summary table
            sport_table_data = []
            for sport, stats in sport_stats.items():
                sport_table_data.append([
                    sport,
                    stats['count'],
                    stats['total_points'],
                    stats['avg_points']
                ])
            
            # Sort by match count (descending)
            sport_table_data.sort(key=lambda x: x[1], reverse=True)
            
            sport_table = tabulate(
                sport_table_data,
                headers=["Sport", "Matches", "Total Points", "Avg Points/Match"],
                tablefmt="grid"
            )
            
            # Display both tables
            logger.info("\n===== MATCH SUMMARY STATISTICS =====")
            logger.info("Top matches by total score:")
            logger.info("\n" + table)
            
            logger.info("\nStatistics by sport:")
            logger.info("\n" + sport_table)
            logger.info("==================================")
        else:
            logger.info("No match statistics available.")

    def display_match_status_summary(self, live_matches: List[Dict]) -> None:
        """
        Display a summary of all tracked matches and their current status
        
        Args:
            live_matches: List of live match data from the API
        """
        if not live_matches:
            logger.info("No live matches found for status summary.")
            return
        
        # Log the total number of matches received
        logger.info(f"Received {len(live_matches)} live matches for status summary")
        
        # Filter matches to only those we're tracking
        tracked_matches = []
        for match in live_matches:
            # Log match details for debugging
            match_id = str(match.get('id', 'unknown'))
            home_team = match.get('home_name', match.get('home', 'Unknown'))
            away_team = match.get('away_name', match.get('away', 'Unknown'))
            
            # Check if we should track this match
            should_track = self.match_filter.should_track_match(match)
            
            # Log the decision
            if should_track:
                logger.info(f"Including match {match_id}: {home_team} vs {away_team} in status summary")
                tracked_matches.append(match)
            elif self.config.debug_mode:
                logger.info(f"Excluding match {match_id}: {home_team} vs {away_team} from status summary")
        
        if not tracked_matches:
            logger.info("No tracked matches currently live.")
            return
        
        # Log how many matches passed the filter
        logger.info(f"Displaying status summary for {len(tracked_matches)} tracked matches")
        
        # Prepare data for tabulate
        status_data = []
        
        for match in tracked_matches:
            match_id = str(match.get('id', ''))
            
            # Get team names with fallbacks
            home_team = match.get('home_name', match.get('home', 'Home Team'))
            away_team = match.get('away_name', match.get('away', 'Away Team'))
            league = match.get('league_name', match.get('competition_name', 'Unknown League'))
            sport = match.get('sport_name', match.get('sport', 'Unknown Sport'))
            
            # Get current score
            current_score = self.extract_score(match)
            score_str = f"{current_score['home']}-{current_score['away']}"
            
            # Get match status and time
            status = match.get('status', 'Unknown')
            match_time = match.get('time', match.get('match_time', ''))
            
            # Add additional status info based on match data
            status_info = status
            if 'minute' in match:
                status_info = f"{status} ({match.get('minute')}′)"
            elif match_time:
                status_info = f"{status} ({match_time})"
            
            # Check if this match has had score notifications
            has_notifications = match_id in self.last_scores
            
            # Create activity indicator based on recent score changes using ASCII alternatives
            activity = "O"  # Default - being tracked (O for Ongoing)
            
            if has_notifications:
                prev_total = self.last_scores[match_id]['home'] + self.last_scores[match_id]['away']
                curr_total = current_score['home'] + current_score['away']
                
                if curr_total > prev_total:
                    activity = "H"  # Hot - recent scoring
                elif curr_total == 0:
                    activity = "C"  # Cold - no scoring yet
            
            # Add to table data
            status_data.append([
                match_id,
                f"{home_team} vs {away_team}",
                sport,
                league[:15] + "..." if len(league) > 18 else league,  # Truncate long league names
                score_str,
                status_info,
                activity
            ])
        
        # Sort by activity level (active matches first)
        def activity_sort_key(row):
            activity = row[6]
            if activity == "H":  # Hot - recent scoring
                return 0  # Active matches first
            elif activity == "O":  # Ongoing - being tracked
                return 1  # Tracked matches next
            else:  # Cold - no scoring yet
                return 2  # Cold matches last
        
        status_data.sort(key=activity_sort_key)
        
        # Create headers with ASCII alternatives instead of emoji for better compatibility
        headers = ["ID", "Teams", "Sport", "League", "Score", "Status", "Activity"]
        
        # Create and display the table
        table = tabulate(status_data, headers=headers, tablefmt="grid")
        
        logger.info("\n===== LIVE MATCH STATUS SUMMARY =====")
        logger.info(f"Tracking {len(status_data)} live matches:")
        logger.info("\n" + table)
        logger.info("Activity Legend: H = Hot (recent scoring), O = Ongoing (being tracked), C = Cold (no score yet)")
        logger.info("=====================================")

def configure_sports_tracking() -> Dict:
    """Interactive configuration for selecting sports to track (minimum 1)"""
    # Define available sports options
    available_sports = [
        "soccer", "basketball", "tennis", "hockey", "baseball", 
        "american_football", "rugby", "cricket", "golf", "volleyball"
    ]
    
    sports_config = {
        "sports": []  # Will be filled with at least 1 sport or set to None for ALL
    }
    
    print("\nSports Tracking Configuration")
    print("----------------------------")
    print("You must select at least 1 sport to track or choose 'ALL' to track all sports.")
    
    # Create a table of available sports
    sports_table = []
    sports_table.append([0, "ALL (track all sports)"])
    for i, sport in enumerate(available_sports, 1):
        sports_table.append([i, sport])
    
    # Display sports in a table format
    print("Available options:")
    print(tabulate(sports_table, headers=["#", "Sport"], tablefmt="grid"))
    
    selected_sports = []
    all_sports_selected = False
    
    while len(selected_sports) < 1 and not all_sports_selected:
        if selected_sports:
            print(f"\nYou've selected {len(selected_sports)} sport(s): {', '.join(selected_sports)}")
        
        print("\nSelect sports (comma-separated numbers or names, or '0' or 'ALL' for all sports):")
        sports_input = input("Enter your selection: ").strip()
        
        if sports_input.lower() in ("0", "all"):
            all_sports_selected = True
            break
        
        if sports_input:
            # Handle both number inputs and sport name inputs
            for item in sports_input.split(","):
                item = item.strip()
                if item.lower() in ("0", "all"):
                    all_sports_selected = True
                    selected_sports = []  # Clear any selected sports
                    break
                
                try:
                    # If it's a number, get the sport at that index
                    index = int(item) - 1
                    if 0 <= index < len(available_sports):
                        sport_name = available_sports[index]
                        if sport_name not in selected_sports:
                            selected_sports.append(sport_name)
                        else:
                            print(f"Warning: {sport_name} is already selected")
                    else:
                        print(f"Warning: {item} is not a valid option number")
                except ValueError:
                    # If it's not a number, check if it's a valid sport name
                    sport_name = item.lower()
                    if sport_name in available_sports:
                        if sport_name not in selected_sports:
                            selected_sports.append(sport_name)
                        else:
                            print(f"Warning: {sport_name} is already selected")
                    else:
                        print(f"Warning: {item} is not a recognized sport")
            
            # If ALL was selected, break out of the loop
            if all_sports_selected:
                break
    
    if all_sports_selected:
        sports_config["sports"] = None
        print("\nYou will track ALL sports.")
    else:
        sports_config["sports"] = selected_sports
        print(f"\nYou will track {len(selected_sports)} sport(s): {', '.join(selected_sports)}")
    
    return sports_config


def configure_match_tracking() -> Dict:
    """Interactive configuration for selecting which matches to track"""
    tracking_config = {
        "track_all_matches": True,
        "tracked_teams": [],
        "tracked_leagues": [],
        "tracked_match_ids": [],
        "exclude_teams": [],
        "exclude_leagues": []
    }
    
    print("\nMatch Tracking Configuration")
    print("---------------------------")
    
    # First, determine tracking mode
    track_all = input("Do you want to track all matches? (Y/n): ").strip().lower()
    if track_all in ("n", "no"):
        tracking_config["track_all_matches"] = False
        
        # If not tracking all, ask for specific teams or leagues
        print("\nYou've chosen to track specific matches only.")
        
        # Teams to track
        teams_input = input("Enter team names to track (comma-separated, leave blank for none): ").strip()
        if teams_input:
            tracking_config["tracked_teams"] = [team.strip() for team in teams_input.split(",")]
        
        # Leagues to track
        leagues_input = input("Enter leagues to track (comma-separated, leave blank for none): ").strip()
        if leagues_input:
            tracking_config["tracked_leagues"] = [league.strip() for league in leagues_input.split(",")]
        
        # Match IDs to track
        match_ids_input = input("Enter specific match IDs to track (comma-separated, leave blank for none): ").strip()
        if match_ids_input:
            tracking_config["tracked_match_ids"] = [match_id.strip() for match_id in match_ids_input.split(",")]
    
    # Regardless of tracking mode, ask for exclusions
    print("\nYou can exclude specific teams or leagues from tracking.")
    
    # Teams to exclude
    exclude_teams_input = input("Enter team names to exclude (comma-separated, leave blank for none): ").strip()
    if exclude_teams_input:
        tracking_config["exclude_teams"] = [team.strip() for team in exclude_teams_input.split(",")]
    
    # Leagues to exclude
    exclude_leagues_input = input("Enter leagues to exclude (comma-separated, leave blank for none): ").strip()
    if exclude_leagues_input:
        tracking_config["exclude_leagues"] = [league.strip() for league in exclude_leagues_input.split(",")]
    
    # Display the configuration summary using tabulate
    print("\nMatch Tracking Configuration Summary:")
    
    table_data = []
    table_data.append(["Tracking Mode", "Specific matches only" if not tracking_config["track_all_matches"] else "All matches"])
    
    if not tracking_config["track_all_matches"]:
        if tracking_config["tracked_teams"]:
            table_data.append(["Teams to Track", ", ".join(tracking_config["tracked_teams"])])
        if tracking_config["tracked_leagues"]:
            table_data.append(["Leagues to Track", ", ".join(tracking_config["tracked_leagues"])])
        if tracking_config["tracked_match_ids"]:
            table_data.append(["Match IDs to Track", ", ".join(tracking_config["tracked_match_ids"])])
    
    if tracking_config["exclude_teams"]:
        table_data.append(["Teams to Exclude", ", ".join(tracking_config["exclude_teams"])])
    if tracking_config["exclude_leagues"]:
        table_data.append(["Leagues to Exclude", ", ".join(tracking_config["exclude_leagues"])])
    
    print(tabulate(table_data, tablefmt="grid"))
    
    return tracking_config


def save_config(config: Dict, filename: str = "config.json") -> None:
    """Save configuration to a JSON file"""
    try:
        # If the file already exists, load it first to preserve other settings
        if os.path.exists(filename):
            with open(filename, "r") as f:
                existing_config = json.load(f)
                # Update existing config with new values
                existing_config.update(config)
                config = existing_config
        
        with open(filename, "w") as f:
            json.dump(config, f, indent=4)
            
        print(f"Configuration saved to {filename}")
    except Exception as e:
        print(f"Error saving configuration: {e}")


def display_tracking_summary(config: Config) -> None:
    """Display a summary of what's being tracked using tabulate"""
    print("\nTracking Summary")
    print("---------------")
    
    # Prepare data for tabulate
    table_data = []
    
    # Display sports being tracked
    if config.sports is None:
        table_data.append(["Sports", "ALL sports"])
    elif len(config.sports) == 0:
        table_data.append(["Sports", "ERROR: No sports selected. Please reconfigure to select at least 1 sport."])
    else:
        table_data.append(["Sports", f"{len(config.sports)} sport(s): {', '.join(config.sports)}"])
    
    # Tracking mode
    if config.track_all_matches:
        table_data.append(["Tracking Mode", "All live matches"])
        
        # Exclusions
        if config.exclude_teams:
            table_data.append(["Excluded Teams", ", ".join(config.exclude_teams)])
        
        if config.exclude_leagues:
            table_data.append(["Excluded Leagues", ", ".join(config.exclude_leagues)])
    else:
        table_data.append(["Tracking Mode", "Specific matches only"])
        
        # Inclusions
        if config.tracked_teams:
            table_data.append(["Tracked Teams", ", ".join(config.tracked_teams)])
            
        if config.tracked_leagues:
            table_data.append(["Tracked Leagues", ", ".join(config.tracked_leagues)])
            
        if config.tracked_match_ids:
            table_data.append(["Tracked Match IDs", ", ".join(config.tracked_match_ids)])
            
        if not (config.tracked_teams or config.tracked_leagues or config.tracked_match_ids):
            table_data.append(["WARNING", "No specific matches, teams, or leagues selected for tracking!"])
    
    # Notification settings
    table_data.append(["Notification Threshold", f"{config.notification_threshold} points"])
    table_data.append(["Polling Interval", f"{config.polling_interval} seconds"])
    
    # Create and display the table
    table = tabulate(table_data, tablefmt="grid")
    print(table)


def load_config() -> Config:
    """Load configuration from environment variables or config file"""
    # Try to load from config file first
    config_file = os.path.join(os.path.dirname(__file__), "config.json")
    
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                config_data = json.load(f)
                
            return Config(
                api_key=config_data.get("api_key", ""),
                api_secret=config_data.get("api_secret", ""),
                notification_threshold=config_data.get("notification_threshold", 2),
                polling_interval=config_data.get("polling_interval", 10.0),
                sports=config_data.get("sports"),
                tracked_teams=config_data.get("tracked_teams", []),
                tracked_leagues=config_data.get("tracked_leagues", []),
                tracked_match_ids=config_data.get("tracked_match_ids", []),
                exclude_teams=config_data.get("exclude_teams", []),
                exclude_leagues=config_data.get("exclude_leagues", []),
                track_all_matches=config_data.get("track_all_matches", True),
                max_concurrent_requests=config_data.get("max_concurrent_requests", 5),
                max_retries=config_data.get("max_retries", 3),
                retry_delay=config_data.get("retry_delay", 2.0),
                cache_expiry=config_data.get("cache_expiry", 60),
                debug_mode=config_data.get("debug_mode", False)
            )
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
    
    # Fall back to environment variables
    return Config(
        api_key=os.environ.get("LIVE_SCORE_API_KEY", ""),
        api_secret=os.environ.get("LIVE_SCORE_API_SECRET", ""),
        notification_threshold=int(os.environ.get("NOTIFICATION_THRESHOLD", "2")),
        polling_interval=float(os.environ.get("POLLING_INTERVAL", "10.0")),
        sports=os.environ.get("SPORTS", "").split(",") if os.environ.get("SPORTS") else None,
        tracked_teams=os.environ.get("TRACKED_TEAMS", "").split(",") if os.environ.get("TRACKED_TEAMS") else [],
        tracked_leagues=os.environ.get("TRACKED_LEAGUES", "").split(",") if os.environ.get("TRACKED_LEAGUES") else [],
        tracked_match_ids=os.environ.get("TRACKED_MATCH_IDS", "").split(",") if os.environ.get("TRACKED_MATCH_IDS") else [],
        exclude_teams=os.environ.get("EXCLUDE_TEAMS", "").split(",") if os.environ.get("EXCLUDE_TEAMS") else [],
        exclude_leagues=os.environ.get("EXCLUDE_LEAGUES", "").split(",") if os.environ.get("EXCLUDE_LEAGUES") else [],
        track_all_matches=os.environ.get("TRACK_ALL_MATCHES", "true").lower() in ("true", "1", "yes"),
        max_concurrent_requests=int(os.environ.get("MAX_CONCURRENT_REQUESTS", "5")),
        max_retries=int(os.environ.get("MAX_RETRIES", "3")),
        retry_delay=float(os.environ.get("RETRY_DELAY", "2.0")),
        cache_expiry=int(os.environ.get("CACHE_EXPIRY", "60")),
        debug_mode=os.environ.get("DEBUG_MODE", "").lower() in ("true", "1", "yes")
    )


def setup_credentials() -> Dict[str, str]:
    """Interactive setup for API credentials"""
    print("\nAPI Credential Setup")
    print("-------------------")
    print("You need a valid API key and secret from live-score-api.com")
    
    api_key = input("Enter your API key: ").strip()
    api_secret = input("Enter your API secret: ").strip()
    
    # Display the credentials summary using tabulate
    print("\nAPI Credentials Summary:")
    
    # Mask the credentials for display (show only first 4 and last 4 characters)
    def mask_credential(cred):
        if len(cred) <= 8:
            return "*" * len(cred)
        return cred[:4] + "*" * (len(cred) - 8) + cred[-4:]
    
    table_data = [
        ["API Key", mask_credential(api_key)],
        ["API Secret", mask_credential(api_secret)]
    ]
    
    print(tabulate(table_data, tablefmt="grid"))
    
    return {
        "api_key": api_key,
        "api_secret": api_secret
    }


def setup_notification_options() -> Dict:
    """Interactive setup for notification options"""
    options = {}
    
    print("\nNotification Options")
    print("-------------------")
    
    # Notification threshold
    while True:
        try:
            threshold = input("Points threshold for notifications (default: 2): ").strip()
            if not threshold:
                options["notification_threshold"] = 2
                break
                
            threshold_val = int(threshold)
            if threshold_val <= 0:
                print("Threshold must be a positive number.")
                continue
                
            options["notification_threshold"] = threshold_val
            break
        except ValueError:
            print("Please enter a valid number.")
    
    # Polling interval
    while True:
        try:
            interval = input("Polling interval in seconds (default: 10): ").strip()
            if not interval:
                options["polling_interval"] = 10.0
                break
                
            interval_val = float(interval)
            if interval_val < 5.0:
                print("Warning: Values less than 5 seconds may exceed API rate limits.")
                confirm = input("Continue with this value? (y/N): ").strip().lower()
                if confirm not in ("y", "yes"):
                    continue
                    
            options["polling_interval"] = interval_val
            break
        except ValueError:
            print("Please enter a valid number.")
    
    # Debug mode
    debug = input("Enable debug mode for detailed logging? (y/N): ").strip().lower()
    options["debug_mode"] = debug in ("y", "yes")
    
    # Display the notification options summary using tabulate
    print("\nNotification Options Summary:")
    
    table_data = [
        ["Notification Threshold", f"{options['notification_threshold']} points"],
        ["Polling Interval", f"{options['polling_interval']} seconds"],
        ["Debug Mode", "Enabled" if options["debug_mode"] else "Disabled"]
    ]
    
    print(tabulate(table_data, tablefmt="grid"))
    
    return options


def main():
    """Main entry point for the score tracker bot"""
    print("Live Match Score Tracker Bot")
    print("----------------------------")
    
    # Check if config file exists
    config_file = os.path.join(os.path.dirname(__file__), "config.json")
    config_exists = os.path.exists(config_file)
    
    if not config_exists:
        print("No configuration found. Let's set up the tracker.")
        
        # Set up API credentials
        credentials = setup_credentials()
        
        # Set up notification options
        notification_options = setup_notification_options()
        
        # Set up sports tracking options - must select exactly 5 sports
        sports_options = configure_sports_tracking()
        
        # Set up match tracking options
        tracking_options = configure_match_tracking()
        
        # Combine all options
        config_data = {**credentials, **notification_options, **sports_options, **tracking_options}
        
        # Save configuration
        save_config(config_data)
    else:
        # If config exists, ask if user wants to reconfigure
        print("\nReconfiguration Options")
        print("----------------------")
        
        # Always ask about sports tracking first to ensure at least 1 sport is selected
        config = load_config()
        if config.sports is None:
            reconfigure_sports = input("You're currently tracking ALL sports.\nDo you want to select different sports? (y/N): ").strip().lower()
            if reconfigure_sports in ("y", "yes"):
                sports_options = configure_sports_tracking()
                save_config(sports_options)
        elif len(config.sports) < 1:
            print("You must select at least 1 sport to track.")
            sports_options = configure_sports_tracking()
            save_config(sports_options)
        else:
            reconfigure_sports = input(f"You're currently tracking {len(config.sports)} sport(s): {', '.join(config.sports)}.\nDo you want to select different sports? (y/N): ").strip().lower()
            if reconfigure_sports in ("y", "yes"):
                sports_options = configure_sports_tracking()
                save_config(sports_options)
        
        # Ask about match tracking
        reconfigure_matches = input("Do you want to reconfigure which matches to track? (y/N): ").strip().lower()
        if reconfigure_matches in ("y", "yes"):
            tracking_options = configure_match_tracking()
            save_config(tracking_options)
    
    # Load configuration
    config = load_config()
    
    # Validate configuration
    if not config.api_key or not config.api_secret:
        print("Error: API key and secret are required.")
        print("Set them in config.json or as environment variables:")
        print("  LIVE_SCORE_API_KEY and LIVE_SCORE_API_SECRET")
        return
    
    # Display tracking summary
    display_tracking_summary(config)
    
    # Create score tracker
    tracker = ScoreTracker(config)
    
    try:
        # Start tracking
        tracker.start()
        
        print("\nLive score tracking started...")
        print("Press Ctrl+C to stop tracking")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping tracker...")
        tracker.stop()
        print("Tracker stopped")


if __name__ == "__main__":
    main()
