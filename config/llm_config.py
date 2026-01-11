import os
import time
import json
from typing import List, Optional, Dict, Any
from openai import OpenAI, RateLimitError, APIError
from core.monitor import monitor

class Validator:
    """Standardized result validation."""
    
    @staticmethod
    def validate_json(content: str, required_keys: List[str] = None) -> Dict[str, Any]:
        """
        Validate if the content is valid JSON and contains required keys.
        Returns parsed JSON dict or raises ValueError.
        """
        try:
            # Clean markdown code blocks if present
            cleaned = content.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            
            data = json.loads(cleaned)
            
            if required_keys:
                missing = [key for key in required_keys if key not in data]
                if missing:
                    raise ValueError(f"Missing required keys: {', '.join(missing)}")
            
            return data
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")

class RateLimiter:
    """Simple rate limiter to control request frequency."""
    
    def __init__(self, min_interval: float = 1.0):
        self.min_interval = min_interval
        self.last_request_time = {}

    def wait(self, model_key: str):
        """Wait if necessary to respect the minimum interval for the given model."""
        now = time.time()
        last = self.last_request_time.get(model_key, 0)
        elapsed = now - last
        
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
            
        self.last_request_time[model_key] = time.time()

class LLMConfig:
    """
    LLM Configuration Manager.
    LLM 配置管理器。
    """
    # Context Management / 上下文管理
    DEFAULT_CONTEXT_WINDOW_CHARS = 50000 # Approx 30k-40k tokens
    
    # Defaults / 默认值
    SHOW_THINKING = True
    AUTHOR_MODEL_KEY = "doubao"
    REVIEWER_MODEL_KEY = "doubao"
    FALLBACK_ORDER = []
    MODELS = {}

    @classmethod
    def load_config(cls):
        """
        Load configuration from JSON file (supports comments).
        从 JSON 文件加载配置（支持注释）。
        """
        config_path = os.path.join(os.path.dirname(__file__), 'llm.json')
        if not os.path.exists(config_path):
             demo_path = os.path.join(os.path.dirname(__file__), 'llm-demo.json')
             if os.path.exists(demo_path):
                 print(f"Warning: config/llm.json not found, using {demo_path}")
                 config_path = demo_path
             else:
                 # Try old name for backward compatibility
                 demo_config_path = os.path.join(os.path.dirname(__file__), 'llm-demo.config')
                 if os.path.exists(demo_config_path):
                     print(f"Warning: config/llm.json not found, using {demo_config_path}")
                     config_path = demo_config_path
                 else:
                     print("Error: config/llm.json not found.")
                     return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Remove comments (// ... and /* ... */)
            import re
            content_no_comments = re.sub(r'//.*?$|/\*.*?\*/', '', content, flags=re.MULTILINE|re.DOTALL)
            
            data = json.loads(content_no_comments)
            cls.MODELS = data.get("models", {})
            active = data.get("active_config", {})
            cls.AUTHOR_MODEL_KEY = active.get("author_model_key", cls.AUTHOR_MODEL_KEY)
            cls.REVIEWER_MODEL_KEY = active.get("reviewer_model_key", cls.REVIEWER_MODEL_KEY)
            cls.SHOW_THINKING = active.get("show_thinking", cls.SHOW_THINKING)
            cls.FALLBACK_ORDER = data.get("fallback_order", cls.FALLBACK_ORDER)
        except Exception as e:
            print(f"Error loading config: {e}")

    @classmethod
    def get_config(cls, key):
        """
        Get configuration for a specific model.
        获取特定模型的配置。
        """
        return cls.MODELS.get(key, cls.MODELS.get("doubao", {})) # Fallback to empty dict if doubao missing

    @classmethod
    def get_available_models(cls):
        """
        Get list of available model keys.
        获取可用模型键列表。
        """
        return list(cls.MODELS.keys())
    
    @classmethod
    def set_show_thinking(cls, show: bool):
        """
        Enable or disable thinking process display.
        启用或禁用思考过程显示。
        """
        cls.SHOW_THINKING = show

    @classmethod
    def set_author_model(cls, key):
        """
        Set the active author model.
        设置当前作者模型。
        """
        if key in cls.MODELS:
            old = cls.AUTHOR_MODEL_KEY
            cls.AUTHOR_MODEL_KEY = key
            monitor.log_switch(old, key, "Manual/Config Change")
            return True
        return False

    @classmethod
    def set_reviewer_model(cls, key):
        """
        Set the active reviewer model.
        设置当前审核模型。
        """
        if key in cls.MODELS:
            old = cls.REVIEWER_MODEL_KEY
            cls.REVIEWER_MODEL_KEY = key
            monitor.log_switch(old, key, "Manual/Config Change")
            return True
        return False

    @classmethod
    def switch_to_next_model(cls, current_key: str, reason: str) -> str:
        """
        Switch to the next available model in fallback order.
        切换到回退顺序中的下一个可用模型。
        """
        try:
            current_idx = cls.FALLBACK_ORDER.index(current_key)
            next_idx = (current_idx + 1) % len(cls.FALLBACK_ORDER)
            next_key = cls.FALLBACK_ORDER[next_idx]
        except ValueError:
            next_key = cls.FALLBACK_ORDER[0] if cls.FALLBACK_ORDER else current_key
            
        monitor.log_switch(current_key, next_key, reason)
        
        if cls.AUTHOR_MODEL_KEY == current_key:
            cls.AUTHOR_MODEL_KEY = next_key
        if cls.REVIEWER_MODEL_KEY == current_key:
            cls.REVIEWER_MODEL_KEY = next_key
            
        return next_key

# Load config on module import
LLMConfig.load_config()

class LLMClient:
    def __init__(self):
        self.clients = {}
        self.rate_limiter = RateLimiter()
        self.validator = Validator()
        
    def _get_client(self, model_key):
        if model_key not in self.clients:
            config = LLMConfig.get_config(model_key)
            self.clients[model_key] = OpenAI(
                api_key=config["api_key"],
                base_url=config["base_url"]
            )
        return self.clients[model_key], LLMConfig.get_config(model_key)["model_name"]

    def test_connection(self, model_key):
        """Test connection to a specific model"""
        try:
            client, model_name = self._get_client(model_key)
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5
            )
            return True, "OK"
        except Exception as e:
            return False, str(e)

    def chat_author(self, messages, temperature=0.7, stream=False):
        """Send chat request to Author LLM with auto-retry and switching"""
        return self._chat_with_retry(LLMConfig.AUTHOR_MODEL_KEY, messages, temperature, stream)

    def chat_reviewer(self, messages, temperature=0.3, stream=False):
        """Send chat request to Reviewer LLM with auto-retry and switching"""
        return self._chat_with_retry(LLMConfig.REVIEWER_MODEL_KEY, messages, temperature, stream)

    def _chat_with_retry(self, start_model_key, messages, temperature, stream):
        current_key = start_model_key
        max_model_switches = len(LLMConfig.FALLBACK_ORDER)
        switches = 0

        while switches < max_model_switches:
            # Try current model with retries for Rate Limit
            for attempt in range(3): # Max 3 retries for rate limit
                try:
                    # Rate limiting wait
                    config = LLMConfig.get_config(current_key)
                    self.rate_limiter.min_interval = config.get("min_interval", 1.0)
                    self.rate_limiter.wait(current_key)

                    client, model_name = self._get_client(current_key)
                    start_time = time.time()
                    
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        temperature=temperature,
                        stream=stream
                    )
                    
                    if not stream:
                        duration = time.time() - start_time
                        content = response.choices[0].message.content
                        monitor.log_generation(current_key, "chat", len(str(messages)), len(str(content)), duration)
                        return content
                    else:
                        return response

                except RateLimitError:
                    wait_time = 2 ** (attempt + 1)
                    if wait_time > 60: wait_time = 60
                    monitor.log_rate_limit(current_key, wait_time, attempt + 1)
                    print(f"\n[系统提示] 触发 {current_key} 频率限制，等待 {wait_time} 秒...")
                    time.sleep(wait_time)
                    continue 
                except Exception as e:
                    monitor.log_error(current_key, str(e))
                    print(f"\n[系统提示] 模型 {current_key} 发生错误: {e}")
                    break 
            
            # Switch Model
            reason = "API Error / Rate Limit Exhausted"
            old_key = current_key
            current_key = LLMConfig.switch_to_next_model(old_key, reason)
            switches += 1
            print(f"[系统提示] 自动切换至备用模型: {current_key}")
            
        return f"Error: All models failed after {switches} switches."

# Global instance
llm_client = LLMClient()
