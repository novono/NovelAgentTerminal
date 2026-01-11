import json
from rich.panel import Panel
from agents.base import BaseAgent
import config.prompt_config as prompt_config

class ReviewAgent(BaseAgent):
    """
    Handles chapter review, scoring, and revision.
    """
    
    def review_chapter(self, content, context_data, novel_type="long"):
        """Reviews the chapter and returns a score and feedback."""
        sys_prompt = prompt_config.SHORT_NOVEL_REVIEW_SYSTEM if novel_type == "short" else prompt_config.CHAPTER_REVIEW_SYSTEM
        
        messages = [
            {"role": "system", "content": sys_prompt.content},
            {"role": "user", "content": f"【待审核章节】\n{content}\n\n【上下文】\n{json.dumps(context_data, ensure_ascii=False)}"}
        ]
        
        res = self.chat(messages, description="正在审核章节...")
        return self.parse_json_safe(res) or {"score": 0, "passed": False, "comments": "Error parsing review"}

    def revise_chapter(self, content, feedback, target_words=2000):
        """Revises the chapter based on feedback."""
        messages = [
            {"role": "system", "content": prompt_config.CHAPTER_REVISE_SYSTEM.content},
            {"role": "user", "content": f"原文：\n{content}\n\n意见：\n{json.dumps(feedback, ensure_ascii=False)}\n\n目标字数：{target_words}"}
        ]
        
        return self.chat(messages, description="正在根据意见精修章节...", target_length=target_words)

    def evaluate_instability(self, content):
        """Evaluates a proposed instability factor."""
        messages = [
            {"role": "system", "content": prompt_config.INSTABILITY_EVAL_SYSTEM.content},
            {"role": "user", "content": f"{content}"}
        ]
        
        res = self.chat(messages, description="正在评估神之一手...")
        return self.parse_json_safe(res) or {"score": 0, "comments": "Error"}

    def generate_summary(self, content):
        """Generates detailed summary for a chapter."""
        messages = [
            {"role": "system", "content": prompt_config.DETAILED_SUMMARY_SYSTEM.content},
            {"role": "user", "content": content}
        ]
        response = self.chat(messages, description="正在生成章节详细索引...")
        return self.parse_json_safe(response) or {"summary": "解析失败", "key_events": [], "plot_progression_score": 0}
