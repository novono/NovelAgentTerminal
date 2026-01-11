import json
import random
from rich.panel import Panel
from agents.base import BaseAgent
import config.prompt_config as prompt_config

class WriterAgent(BaseAgent):
    """
    Handles actual chapter writing and instability injection.
    处理实际章节写作和不稳定因素注入。
    """
    
    def write_chapter(self, context, chap_num, pacing_guidance, target_words=None):
        """Generates the chapter content."""
        """生成章节内容。"""
        
        # 1. Determine target words dynamically from config if not provided or to override
        # 1. 动态确定目标字数（如果没有提供或需要覆盖）
        # If target_words is passed (e.g. from test or manual override), use it.
        # 如果传入了 target_words（例如来自测试或手动覆盖），则使用它。
        # Otherwise, fetch from setting.json (prioritize config.chapter_words, fallback to root chapter_words)
        # 否则，从 setting.json 获取（优先 config.chapter_words，回退到根 chapter_words）
        if target_words is None:
            target_words = self.data_manager.get_config_value("setting.config.chapter_words")
            if target_words is None:
                target_words = self.data_manager.get_config_value("setting.chapter_words", 2000)
            
        # Ensure it's an integer
        # 确保是整数
        target_words = int(target_words)

        messages = [
            {"role": "system", "content": prompt_config.CHAPTER_GEN_SYSTEM.content.format(target_words=target_words)},
            {"role": "user", "content": f"【第 {chap_num} 章创作指令】\n\n{pacing_guidance}\n\n{context}"}
        ]
        
        content = self.chat(messages, description=f"正在撰写第 {chap_num} 章正文 (目标字数: {target_words})...", target_length=target_words)
        return self._enforce_word_count(content, target_words)

    def _enforce_word_count(self, content, target_words):
        """Check word count and trigger expand/compress if needed."""
        """检查字数，如果需要则触发扩写或精简。"""
        max_retries = 2
        
        for i in range(max_retries):
            current_len = len(content)
            # Thresholds: +/- 20%
            # 阈值：+/- 20%
            lower_bound = int(target_words * 0.8)
            upper_bound = int(target_words * 1.2)
            
            if lower_bound <= current_len <= upper_bound:
                return content
            
            if current_len < lower_bound:
                self.console.print(Panel(f"⚠️ 字数不足 ({current_len}/{target_words})，触发自动扩写 (第 {i+1} 轮)...", style="yellow"))
                # Use format to inject variables into template
                # 使用 format 注入变量到模板
                prompt_content = prompt_config.CHAPTER_EXPAND_SYSTEM.content.format(
                    content=content, 
                    target_words=target_words
                )
                messages = [{"role": "user", "content": prompt_content}]
                content = self.chat(messages, description="正在扩写...", target_length=target_words)
                
            elif current_len > upper_bound:
                self.console.print(Panel(f"⚠️ 字数过多 ({current_len}/{target_words})，触发自动精简 (第 {i+1} 轮)...", style="yellow"))
                prompt_content = prompt_config.CHAPTER_COMPRESS_SYSTEM.content.format(
                    content=content, 
                    target_words=target_words
                )
                messages = [{"role": "user", "content": prompt_content}]
                content = self.chat(messages, description="正在精简...", target_length=target_words)
        
        return content

    def generate_instability(self, current_plot):
        """Generates a plot twist."""
        """生成剧情转折（神之一手）。"""
        messages = [
            {"role": "system", "content": prompt_config.INSTABILITY_GEN_SYSTEM.content},
            {"role": "user", "content": f"当前剧情：\n{current_plot}"}
        ]
        
        res = self.chat(messages, description="正在构思神之一手...")
        return self.parse_json_safe(res) or None

    def integrate_instability(self, original_content, instability_content):
        """Merges the twist into the chapter."""
        """将转折融合到章节中。"""
        messages = [
            {"role": "system", "content": prompt_config.INSTABILITY_INTEGRATE_SYSTEM.content},
            {"role": "user", "content": f"原文：\n{original_content}\n\n神之一手：\n{instability_content}"}
        ]
        
        return self.chat(messages, description="正在融合神之一手...")

    def check_instability_trigger(self, position="pre", miss_count=0):
        """Check if instability factor should be triggered."""
        """检查是否应触发不稳定因素。"""
        author_config = self.data_manager.get_author().get("config", {})
        if not author_config.get("enable_instability", False):
            return False

        base_prob = prompt_config.INSTABILITY_CONFIG.get(f"{position}_write_prob", 0.15)
        
        # Boost logic: +10% if missed 3 times
        # 概率提升逻辑：如果错过 3 次，增加 10%
        current_prob = base_prob
        if miss_count >= 3:
            boost = prompt_config.INSTABILITY_CONFIG.get("prob_boost", 0.10)
            current_prob += boost
            
        return random.random() < current_prob
