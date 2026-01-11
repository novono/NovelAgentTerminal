from typing import List, Dict, Any
from .base import BaseAgent
from rich.panel import Panel
from rich.markdown import Markdown
import config.prompt_config as prompt_config
import json

class DiscussionAgent(BaseAgent):
    """
    Agent responsible for facilitating a multi-agent discussion to brainstorm plot ideas
    and generate structured chapter plans.
    """

    def __init__(self, data_manager):
        super().__init__(data_manager)
        self.experts = {
            "plot": prompt_config.DISCUSSION_PLOT_EXPERT,
            "character": prompt_config.DISCUSSION_CHARACTER_EXPERT,
            "world": prompt_config.DISCUSSION_WORLD_EXPERT
        }

    def run_discussion(self, context: str, topic: str, rounds: int = 1) -> str:
        """
        Runs a multi-turn discussion among experts.
        
        Args:
            context: The current story context (summary, setting, etc.)
            topic: The goal of this discussion (e.g., "Plan Chapter 10")
            rounds: How many rounds of discussion to hold.
            
        Returns:
            A summary of the discussion.
        """
        self.console.print(Panel(f"开启剧情研讨会: {topic}", style="bold magenta"))
        
        discussion_log = []
        
        # Initial Context for the experts
        base_prompt = f"背景信息：\n{context}\n\n本次研讨议题：{topic}"
        
        current_context = base_prompt
        
        for r in range(rounds):
            self.console.print(f"[bold]--- 第 {r+1} 轮讨论 ---[/bold]")
            
            # 1. Plot Expert
            plot_response = self._consult_expert("plot", current_context)
            self._print_expert_opinion("剧情策划", plot_response)
            discussion_log.append(f"【剧情策划】: {plot_response}")
            current_context += f"\n\n剧情策划意见：{plot_response}"
            
            # 2. Character Expert
            char_response = self._consult_expert("character", current_context)
            self._print_expert_opinion("角色设计", char_response)
            discussion_log.append(f"【角色设计】: {char_response}")
            current_context += f"\n\n角色设计意见：{char_response}"
            
            # 3. World Expert
            world_response = self._consult_expert("world", current_context)
            self._print_expert_opinion("世界观架构", world_response)
            discussion_log.append(f"【世界观架构】: {world_response}")
            current_context += f"\n\n世界观架构意见：{world_response}"

        # Summarize
        self.console.print("[bold magenta]正在汇总研讨结论...[/bold magenta]")
        summary = self._summarize_discussion(current_context)
        return summary

    def _consult_expert(self, expert_type: str, context: str) -> str:
        """Get opinion from a specific expert persona."""
        sys_prompt = self.experts[expert_type]
        messages = [
            {"role": "system", "content": sys_prompt.content},
            {"role": "user", "content": context}
        ]
        response = self.chat(messages, description=f"{expert_type} thinking...")
        return response

    def _print_expert_opinion(self, role_name: str, content: str):
        self.console.print(Panel(Markdown(content), title=f"{role_name} 发言", border_style="blue"))

    def _summarize_discussion(self, discussion_history: str) -> str:
        """Synthesize the discussion into a coherent creative brief."""
        sys_prompt = prompt_config.DISCUSSION_SUMMARY_SYSTEM
        messages = [
            {"role": "system", "content": sys_prompt.content},
            {"role": "user", "content": discussion_history}
        ]
        return self.chat(messages, description="Summarizing discussion...")

    def generate_chapter_plan(self, discussion_summary: str, chapter_num: int, target_words: int) -> Dict[str, Any]:
        """
        Converts the discussion summary into a structured chapter plan.
        """
        sys_prompt = prompt_config.AUTO_CHAPTER_PLANNER
        
        input_content = f"讨论纪要：\n{discussion_summary}\n\n目标章节：第 {chapter_num} 章\n字数要求：{target_words}字"
        
        messages = [
            {"role": "system", "content": sys_prompt.content},
            {"role": "user", "content": input_content}
        ]
        
        response = self.chat(messages, description="Generating chapter plan...")
        
        plan = self.parse_json_safe(response)
        if plan:
            return plan
            
        self.console.print(f"[red]Failed to parse chapter plan[/red]")
        # Fallback
        return {
            "title": f"第 {chapter_num} 章",
            "summary": discussion_summary[:200],
            "structure": "自动生成失败，使用默认结构",
            "core_conflict": "未知"
        }

    def generate_creative_report(self, chapter_plan: Dict[str, Any]) -> str:
        """Generates a human-readable analysis report."""
        sys_prompt = prompt_config.CREATIVE_BRIEF_GENERATOR
        messages = [
            {"role": "system", "content": sys_prompt.content},
            {"role": "user", "content": json.dumps(chapter_plan, ensure_ascii=False)}
        ]
        return self.chat(messages, description="Generating creative report...")
