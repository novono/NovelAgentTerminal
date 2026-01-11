import re
import time
from rich.console import Console
from rich.text import Text
from rich.live import Live
from config.llm_config import llm_client, LLMConfig

console = Console()

class LLMInterface:
    """
    Unified interface for LLM interactions.
    Handles streaming, thinking process display, and JSON cleaning.
    """
    
    @staticmethod
    def chat_with_status(messages, description="正在生成...", target_length=None):
        """Generic LLM chat with real-time status line."""
        full_content = ""
        full_reasoning = ""
        is_thinking = False
        
        # Determine initial status
        model_config = LLMConfig.get_config(LLMConfig.AUTHOR_MODEL_KEY)
        show_thinking = LLMConfig.SHOW_THINKING and model_config.get("supports_thinking", False)
        
        status_text = Text(f"🚀 连接中... {description}", style="bold cyan")
        
        # Use Live with a simple text renderable for single line
        with Live(status_text, refresh_per_second=10) as live:
            time.sleep(0.5) # Connection simulation
            status_text.plain = f"🤔 思考中... {description}"
            live.refresh()
            
            try:
                response_stream = llm_client.chat_author(messages, stream=True)
                
                # Handle non-stream response (error or mock)
                if isinstance(response_stream, str):
                    status_text.plain = f"✅ 完成! {description}"
                    status_text.style = "bold green"
                    live.refresh()
                    return response_stream

                for chunk in response_stream:
                    # Handle Thinking/Reasoning
                    delta = chunk.choices[0].delta
                    
                    # 1. Check for standard reasoning_content (DeepSeek style)
                    reasoning_chunk = getattr(delta, 'reasoning_content', None)
                    if reasoning_chunk:
                        full_reasoning += reasoning_chunk
                        if show_thinking:
                            status_text.plain = f"🧠 思考中... {full_reasoning[-50:].replace(chr(10), ' ')}"
                            live.refresh()
                        continue
                        
                    # 2. Check for content
                    content_chunk = delta.content
                    if content_chunk:
                        # Check for <think> tags in content (Local models sometimes do this)
                        if "<think>" in content_chunk:
                            is_thinking = True
                            content_chunk = content_chunk.replace("<think>", "")
                        
                        if "</think>" in content_chunk:
                            is_thinking = False
                            content_chunk = content_chunk.replace("</think>", "")
                            # Clear thinking status
                            status_text.plain = f"✍️ 生成中... {description}"
                            live.refresh()
                            
                        if is_thinking:
                            full_reasoning += content_chunk
                            if show_thinking:
                                status_text.plain = f"🧠 思考中... {full_reasoning[-50:].replace(chr(10), ' ')}"
                                live.refresh()
                        else:
                            full_content += content_chunk
                            current_len = len(full_content)
                            progress_info = f"({current_len}/{target_length} 字)" if target_length else f"({current_len} 字)"
                            status_text.plain = f"✍️ 生成中... {description} {progress_info}"
                            live.refresh()
                
                status_text.plain = f"✅ 完成! {description} (总字数: {len(full_content)})"
                status_text.style = "bold green"
                live.refresh()
                
            except Exception as e:
                status_text.plain = f"❌ 错误: {str(e)}"
                status_text.style = "bold red"
                live.refresh()
                return f"Error: {str(e)}"
            
        return full_content

    @staticmethod
    def clean_json_response(text: str) -> str:
        """Extract JSON from markdown code blocks if present."""
        match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if match:
            return match.group(1)
        return text
