from rich.console import Console
from core.data_manager import DataManager
from core.llm import LLMInterface
from core.monitor import monitor

console = Console()

class BaseAgent:
    """
    Base class for all agents in the NovelTerminal system.
    NovelTerminal 系统中所有 Agent 的基类。
    
    Provides common access to DataManager, LLM, and Logging.
    提供对数据管理器、LLM 和日志记录的通用访问。
    """
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        self.llm = LLMInterface()
        self.console = console
        self.monitor = monitor

    def log_event(self, event_type: str, details: dict):
        """
        Log a system event.
        记录系统事件。
        """
        self.monitor.log_event(event_type, details)

    def chat(self, messages, description="Processing...", target_length=None):
        """
        Send a chat request to the LLM with a status display.
        向 LLM 发送聊天请求并显示状态。
        """
        return self.llm.chat_with_status(messages, description, target_length)

    def clean_json(self, text: str) -> str:
        """
        Clean JSON string (remove markdown blocks).
        清理 JSON 字符串（移除 Markdown 代码块）。
        """
        return self.llm.clean_json_response(text)

    def parse_json_safe(self, text: str) -> dict:
        """
        Safely parse JSON, handling common LLM errors.
        安全地解析 JSON，处理常见的 LLM 错误。
        """
        import json
        cleaned = self.clean_json(text)
        try:
            # strict=False allows control characters like newlines in strings
            # strict=False 允许字符串中包含控制字符（如换行符）
            return json.loads(cleaned, strict=False)
        except json.JSONDecodeError:
            # If it still fails, try to repair via LLM
            # 如果仍然失败，尝试通过 LLM 进行修复
            self.console.print("[yellow]JSON 解析失败，正在尝试自动修复...[/yellow]")
            return self._repair_json_with_llm(cleaned)

    def _repair_json_with_llm(self, bad_json: str) -> dict:
        """
        Attempt to repair broken JSON using LLM.
        尝试使用 LLM 修复损坏的 JSON。
        """
        import json
        messages = [
            {"role": "system", "content": "You are a JSON fixer. Return ONLY valid JSON. Fix any syntax errors, unescaped quotes, or control characters."},
            {"role": "user", "content": f"Fix this JSON:\n\n{bad_json[:3000]}"} # Truncate if too long
        ]
        fixed = self.chat(messages, description="修复 JSON 数据...")
        cleaned_fixed = self.clean_json(fixed)
        try:
            return json.loads(cleaned_fixed, strict=False)
        except:
            self.console.print("[red]JSON 修复失败，返回空字典。[/red]")
            return {}
