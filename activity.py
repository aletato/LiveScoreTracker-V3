import time
import logging

logger = logging.getLogger("score_tracker")

class ActivityTracker:
    """Tracks and manages match activity states (Hot, Cold, etc.)"""
    
    def __init__(self):
        # Store timestamps of last score changes for "Hot" activity
        self.score_change_times = {}
        
        # Store timestamps of when 0-0 scores were first observed for "Cold" activity
        self.zero_score_start_times = {}
        
        # Duration settings (in seconds)
        self.hot_duration = 300  # 5 minutes - match stays "Hot" after scoring
        self.cold_duration = 1200  # 20 minutes - match becomes "Cold" after 0-0 for this long
    
    def record_score_change(self, match_id):
        """Record a score change for a match, marking it as 'Hot'"""
        match_id_str = str(match_id)
        self.score_change_times[match_id_str] = time.time()
        
        # If score changed, remove from zero_score_start_times if present
        if match_id_str in self.zero_score_start_times:
            del self.zero_score_start_times[match_id_str]
        
        logger.info(f"Setting match {match_id_str} as HOT at {time.strftime('%H:%M:%S')}")
    
    def record_zero_score(self, match_id, current_score):
        """Record when a match has a 0-0 score"""
        match_id_str = str(match_id)
        
        # Only record if this is a 0-0 score and we haven't recorded it yet
        total_score = current_score['home'] + current_score['away']
        if total_score == 0 and match_id_str not in self.zero_score_start_times:
            self.zero_score_start_times[match_id_str] = time.time()
            logger.info(f"Started tracking 0-0 score for match {match_id_str} at {time.strftime('%H:%M:%S')}")
    
    def remove_match(self, match_id):
        """Remove a match from tracking (e.g., when finished)"""
        match_id_str = str(match_id)
        
        if match_id_str in self.score_change_times:
            del self.score_change_times[match_id_str]
            
        if match_id_str in self.zero_score_start_times:
            del self.zero_score_start_times[match_id_str]
    
    def get_activity(self, match_id, current_score):
        """
        Determine the activity status for a match
        
        Returns:
            str: 'H' for Hot, 'C' for Cold, 'O' for Ongoing
        """
        match_id_str = str(match_id)
        current_time = time.time()
        
        # Check if match is "Hot" (recent score change)
        if match_id_str in self.score_change_times:
            time_since_change = current_time - self.score_change_times[match_id_str]
            if time_since_change < self.hot_duration:
                return "H"  # Hot - recent scoring
        
        # Check if match is "Cold" (0-0 for extended period)
        total_score = current_score['home'] + current_score['away']
        if total_score == 0:
            # Record this zero score if not already tracked
            if match_id_str not in self.zero_score_start_times:
                self.zero_score_start_times[match_id_str] = current_time
            
            # Check if it's been 0-0 for longer than cold_duration
            time_at_zero = current_time - self.zero_score_start_times[match_id_str]
            if time_at_zero >= self.cold_duration:
                return "C"  # Cold - no scoring for extended period
        elif match_id_str in self.zero_score_start_times:
            # Score is no longer 0-0, remove from tracking
            del self.zero_score_start_times[match_id_str]
        
        # Default activity
        return "O"  # Ongoing
