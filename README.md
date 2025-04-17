# Live Match Score Tracker Bot

A Python bot that tracks live sports matches and sends notifications when scores change.

## Overview

This bot connects to the live-score-api service to monitor live sports matches and sends notifications when a configurable number of points are scored in a match. It's perfect for sports enthusiasts who want to stay updated on score changes without constantly checking scores manually.

## Features

- **Multi-sport Support**: Track matches across various sports including basketball, soccer, tennis, and more
- **Flexible Match Filtering**: Track specific matches by team name, league, or match ID
- **Real-time Notifications**: Get alerts when scores change
- **Configurable Thresholds**: Set how many points need to be scored before receiving a notification
- **Resilient Error Handling**: Built-in retry logic for API failures
- **Match Statistics**: View summaries of tracked matches and their scores
- **Desktop Notifications**: Receive desktop notifications (platform-specific)

## Requirements

- Python 3.9 or higher
- Required Python packages:
  - requests
  - tabulate
  - Platform-specific notification packages (optional):
    - Windows: win10toast
    - macOS: pync
    - Linux: notify2
- A valid API key for live-score-api.com

## Installation

1. Clone this repository or download the source code
2. Install the required dependencies using the provided requirements.txt file:
   ```
   pip install -r requirements.txt
   ```
3. (Optional) Uncomment and install the appropriate platform-specific notification package in requirements.txt:
   - Windows: win10toast
   - macOS: pync
   - Linux: notify2

## Configuration

Create a `config.json` file in the same directory as the bot with the following structure:

```json
{
    "api_key": "YOUR_API_KEY",
    "api_secret": "YOUR_API_SECRET",
    "notification_threshold": 2,
    "polling_interval": 10.0,
    "sports": ["basketball"],
    "max_concurrent_requests": 5,
    "max_retries": 3,
    "retry_delay": 2.0,
    "cache_expiry": 60,
    "track_all_matches": true,
    "tracked_teams": [],
    "tracked_leagues": [],
    "tracked_match_ids": [],
    "exclude_teams": [],
    "exclude_leagues": [],
    "debug_mode": false
}
```

### Configuration Options

| Option | Description | Type | Default |
|--------|-------------|------|---------|
| `api_key` | Your API key from live-score-api.com | String | Required |
| `api_secret` | Your API secret from live-score-api.com | String | Required |
| `notification_threshold` | Number of points scored before notification | Integer | 2 |
| `polling_interval` | Time between API checks (seconds) | Float | 10.0 |
| `sports` | List of sports to track (null for all sports) | Array or null | null |
| `max_concurrent_requests` | Maximum number of concurrent API requests | Integer | 5 |
| `max_retries` | Maximum number of retries for failed requests | Integer | 3 |
| `retry_delay` | Delay between retries (seconds) | Float | 2.0 |
| `cache_expiry` | Cache expiry time (seconds) | Integer | 60 |
| `track_all_matches` | Whether to track all matches | Boolean | true |
| `tracked_teams` | Teams to track (if not tracking all) | Array | [] |
| `tracked_leagues` | Leagues to track (if not tracking all) | Array | [] |
| `tracked_match_ids` | Specific match IDs to track | Array | [] |
| `exclude_teams` | Teams to exclude from tracking | Array | [] |
| `exclude_leagues` | Leagues to exclude from tracking | Array | [] |
| `debug_mode` | Enable detailed logging | Boolean | false |

## Usage

Run the bot with:

```
python main.py
```

On first run, the bot will guide you through the configuration process if no `config.json` file exists.

### Interactive Configuration

The bot provides an interactive configuration process that will help you set up:

1. API credentials
2. Notification options
3. Sports to track
4. Match filtering options

### Tracking Options

You can configure the bot to:

- Track all matches for selected sports
- Track only specific teams, leagues, or match IDs
- Exclude specific teams or leagues from tracking

## Logging

The bot logs all activity to:
- Console output
- A `score_tracker.log` file

## Notifications

When the configured number of points are scored in a tracked match, the bot will:

1. Log the score change to the console and log file
2. Display a desktop notification (if platform-specific packages are installed)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

