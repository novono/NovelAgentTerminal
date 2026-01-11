import logging
import datetime
import os
import json

class Monitor:
    LOG_FILE = "llm.report"

    def __init__(self):
        self.logger = logging.getLogger("LLMMonitor")
        self.logger.setLevel(logging.INFO)
        
        # Check if handler already exists to avoid duplicates
        if not self.logger.handlers:
            handler = logging.FileHandler(self.LOG_FILE, encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_event(self, event_type: str, details: dict):
        """Generic event logger."""
        message = f"[{event_type}] {json.dumps(details, ensure_ascii=False)}"
        self.logger.info(message)

    def log_switch(self, old_model: str, new_model: str, reason: str):
        """Log LLM switching event."""
        details = {
            "from": old_model,
            "to": new_model,
            "reason": reason
        }
        self.log_event("MODEL_SWITCH", details)

    def log_generation(self, model: str, task_type: str, input_len: int, output_len: int, duration: float, success: bool = True):
        """Log generation metrics."""
        details = {
            "model": model,
            "task": task_type,
            "input_chars": input_len,
            "output_chars": output_len,
            "duration_seconds": round(duration, 2),
            "status": "SUCCESS" if success else "FAILED"
        }
        self.log_event("GENERATION", details)

    def log_rate_limit(self, model: str, wait_time: float, retry_count: int):
        """Log rate limit hit."""
        details = {
            "model": model,
            "wait_time": wait_time,
            "retry_count": retry_count
        }
        self.log_event("RATE_LIMIT", details)

    def log_error(self, model: str, error_msg: str):
        """Log errors."""
        details = {
            "model": model,
            "error": error_msg
        }
        self.logger.error(f"[ERROR] {json.dumps(details, ensure_ascii=False)}")

# Global instance
monitor = Monitor()
