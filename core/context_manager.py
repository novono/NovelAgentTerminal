import json

class ContextManager:
    """
    Manages context size and compression decisions to avoid token exhaustion.
    Inspired by Kimi-Writer's smart context management.
    """
    def __init__(self, max_chars=50000, trigger_ratio=0.8):
        """
        Args:
            max_chars: Estimated character limit for context (safe proxy for tokens).
            trigger_ratio: Ratio of max_chars at which to trigger compression.
        """
        self.max_chars = max_chars
        self.trigger_ratio = trigger_ratio

    def estimate_size(self, text: str) -> int:
        """Estimate size in characters."""
        return len(text)

    def get_context_size(self, settings: str, history: dict) -> int:
        """Calculate total estimated size of the context."""
        rolling_summary = history.get("rolling_summary", "")
        chapters = history.get("chapters", [])
        
        # We usually send recent chapters as JSON or text
        chapters_text = json.dumps(chapters, ensure_ascii=False)
        
        # Total = Settings + Rolling Summary + Active Chapters
        total = len(settings) + len(rolling_summary) + len(chapters_text)
        return total

    def should_compress(self, settings: str, history: dict) -> bool:
        """Check if compression is needed based on size or chapter count."""
        current_size = self.get_context_size(settings, history)
        threshold = self.max_chars * self.trigger_ratio
        
        # Also enforce a hard limit on chapter count (e.g., max 15 active chapters)
        # to prevent infinite growth even if text is short
        chapter_count = len(history.get("chapters", []))
        
        return current_size > threshold or chapter_count >= 15

    def calculate_keep_count(self, settings: str, history: dict, default_keep=5) -> int:
        """
        Determine how many chapters to keep active.
        If context is tight, reduce the number of active chapters.
        """
        current_size = self.get_context_size(settings, history)
        
        # If we are critically close to limit (95%), reduce keep count
        if current_size > self.max_chars * 0.95:
            return max(1, default_keep - 3) # Keep ~2
        
        # If we are just over trigger (80%), reduce slightly
        if current_size > self.max_chars * 0.8:
            return max(2, default_keep - 2) # Keep ~3
            
        return default_keep
