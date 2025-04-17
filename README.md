# 🏆 LiveScoreTracker V4

A powerful Python application that tracks live sports matches and delivers real-time score notifications.

![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## 📋 Overview

LiveScoreTracker V4 connects to the live-score-api service to monitor sports matches in real-time. It automatically sends notifications when scores change, allowing sports enthusiasts to stay updated without constantly checking scores manually.

## ✨ Key Features

- **🏀 Multi-sport Support**: Track matches across basketball, soccer, tennis, and more
- **🔍 Smart Match Filtering**: Focus on specific teams, leagues, or match IDs
- **⚡ Real-time Notifications**: Receive instant alerts when scores change
- **🎚️ Configurable Thresholds**: Customize how many points trigger a notification
- **🔥 Activity Status System**: Visual indicators show match activity (HOT, Ongoing, Cold)
- **🕒 Timezone Intelligence**: Automatic conversion to your local timezone
- **🛡️ Resilient Operation**: Built-in retry logic handles API failures gracefully
- **📊 Match Statistics**: View comprehensive summaries of tracked matches
- **💻 Desktop Notifications**: Platform-specific alerts keep you informed

## 🏗️ Architecture

The project follows a modular design with four core components:

| File | Purpose |
|------|---------|
| **main.py** | Entry point handling configuration, setup, and execution flow |
| **tracking.py** | Core tracking functionality with `ScoreCache`, `LiveScoreAPI`, `MatchFilter`, and `ScoreTracker` |
| **notification_system.py** | Notification handling through the `Notifier` class |
| **timezone_utils.py** | Timezone detection and conversion via `TimezoneConverter` |

This modular approach enhances maintainability and extensibility.

## 📋 Requirements

- Python 3.9+
- Required packages:
  - requests
  - tabulate
  - pytz
  - tzlocal
- Platform-specific notification packages (optional):
  - Windows: win10toast
  - macOS: pync
  - Linux: notify2
- Valid API credentials from live-score-api.com

## 🚀 Getting Started

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/LiveScoreTracker.git
   cd LiveScoreTracker
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. (Optional) Install platform-specific notification package:
   ```bash
   # Windows
   pip install win10toast
   
   # macOS
   pip install pync
   
   # Linux
   pip install notify2
   ```

### Configuration

Create a `config.json` file with your settings:

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
| `api_key` | Your API key | String | Required |
| `api_secret` | Your API secret | String | Required |
| `notification_threshold` | Points before notification | Integer | 2 |
| `polling_interval` | Time between checks (seconds) | Float | 10.0 |
| `sports` | Sports to track | Array | null (all) |
| `max_concurrent_requests` | Max concurrent API requests | Integer | 5 |
| `max_retries` | Max retries for failed requests | Integer | 3 |
| `retry_delay` | Delay between retries (seconds) | Float | 2.0 |
| `cache_expiry` | Cache expiry time (seconds) | Integer | 60 |
| `track_all_matches` | Track all matches flag | Boolean | true |
| `tracked_teams` | Teams to track | Array | [] |
| `tracked_leagues` | Leagues to track | Array | [] |
| `tracked_match_ids` | Match IDs to track | Array | [] |
| `exclude_teams` | Teams to exclude | Array | [] |
| `exclude_leagues` | Leagues to exclude | Array | [] |
| `debug_mode` | Enable detailed logging | Boolean | false |

## 🎮 Usage

Run the application:

```bash
python main.py
```

On first run, the interactive setup will guide you through configuration if no `config.json` exists.

### Tracking Options

Configure the tracker to:
- Monitor all matches for selected sports
- Focus on specific teams, leagues, or match IDs
- Exclude certain teams or leagues

## 📝 Logging

Activity is logged to:
- Console output
- `score_tracker.log` file

## 🔔 Notification System

When the configured threshold of points is scored, the system:
1. Logs the score change
2. Displays a desktop notification (if supported)

## 🔥 Activity Status System V2

The enhanced activity status system provides visual indicators:

- **H (Hot)**: Recent score change (within last 5 minutes)
- **O (Ongoing)**: Active match without recent score changes
- **C (Cold)**: Match with no scoring activity (0-0)

### Match Status Sorting

Matches are sorted by game state in this priority:
1. **NOT STARTED** (upcoming matches)
2. **Half Time Break**
3. **IN PLAY** (active matches)
4. **Added Time** (injury/extra time)
5. Other statuses

### Debug Mode

When enabled, debug mode provides detailed information about:
- Match HOT status checks
- Current HOT matches list
- Timing of status changes
- Match cooldown events

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
