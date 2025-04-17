
"""
Live Match Score Tracker Bot
----------------------------
This bot tracks live matches from live-score-api and sends notifications
when 2 or more points are scored in a match.
----------------------------
"""


import os
import sys
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union, Set, Tuple
from tabulate import tabulate

# Import classes from our modules
from notification_system import Notifier
from tracking import ScoreTracker, LiveScoreAPI, MatchFilter, ScoreCache

# Configure logging
# Import io and sys for UTF-8 stream handling
import io

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
        
        # Set up sports tracking options
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
    
    # Create score tracker and notifier
    notifier = Notifier(config)
    tracker = ScoreTracker(config)
    
    # Connect the notifier to the tracker
    tracker.set_notifier(notifier)
    
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
