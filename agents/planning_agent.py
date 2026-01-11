import json
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.markdown import Markdown
from agents.base import BaseAgent
import config.prompt_config as prompt_config

class PlanningAgent(BaseAgent):
    """
    Handles novel ideation, setting creation, and structure planning.
    """
    
    def generate_ideas(self, requirements, novel_type="long"):
        """Generates 3 novel ideas based on requirements."""
        sys_prompt = prompt_config.SHORT_NOVEL_GEN_SYSTEM if novel_type == "short" else prompt_config.TEMPLATE_GEN_SYSTEM
        
        messages = [
            {"role": "system", "content": sys_prompt.content},
            {"role": "user", "content": f"用户要求：\n{requirements}"}
        ]
        response = self.chat(messages, description="正在构思 3 个创意模板...")
            
        return self.parse_json_safe(response) or []

    def create_setting(self, selected_idea, requirements):
        """Expands a selected idea into a full setting JSON."""
        expand_sys_prompt = prompt_config.SETTING_CREATE_JSON_SYSTEM
        
        full_context = {
            "template": selected_idea,
            "requirements": requirements
        }
        
        current_setting_context = json.dumps(full_context, ensure_ascii=False)
        
        messages = [
            {"role": "system", "content": expand_sys_prompt.content},
            {"role": "user", "content": f"请基于以下信息生成设定集 JSON：\n{current_setting_context}"}
        ]
        
        setting_content = self.chat(messages, description="正在构建世界观与架构...")
        return self.parse_json_safe(setting_content)

    def init_author_profile(self, setting_json):
        """Initializes the AI author persona."""
        sys_prompt = prompt_config.AUTHOR_INIT_JSON_SYSTEM
        novel_meta = json.dumps(setting_json.get("meta", {}), ensure_ascii=False)
        
        messages = [
            {"role": "system", "content": sys_prompt.content},
            {"role": "user", "content": f"小说元数据：\n{novel_meta}"}
        ]
        
        profile_content = self.chat(messages, description="正在构建作者人格...")
        
        profile = self.parse_json_safe(profile_content)
        if not profile:
            profile = {"name": "AI Author", "style_description": "Standard"}
            
        # Set default configuration (User Requirement: Default to False)
        profile["config"] = {
            "enable_instability": False,
            "enable_life_events": False
        }
        return profile

    def plan_structure(self, total_words, chapter_words, setting_summary, novel_type="long"):
        """Plans the chapter/volume structure."""
        if novel_type == "short":
            sys_prompt = prompt_config.SHORT_NOVEL_PLANNING_SYSTEM
        else:
            sys_prompt = prompt_config.NOVEL_PLANNING_SYSTEM
            
        messages = [
            {"role": "system", "content": sys_prompt.content},
            {"role": "user", "content": f"总字数：{total_words}万\n单章：{chapter_words}\n设定：{setting_summary}"}
        ]
        
        plan_content = self.chat(messages, description="正在规划全书结构...")
        return self.parse_json_safe(plan_content) or {}
