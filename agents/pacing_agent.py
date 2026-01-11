import json
import time
from rich.panel import Panel
from rich.markdown import Markdown
from agents.base import BaseAgent
import config.prompt_config as prompt_config

class PacingAgent(BaseAgent):
    """
    Analyzes novel pacing, structure, and author style.
    Handles history compression and life events.
    """
    
    def calculate_pacing_status(self, current_chapter: int, novel_config: dict) -> dict:
        """
        Calculate pacing stage based on progress.
        """
        setting = self.data_manager.get_setting()
        
        # 1. Calculate Total Chapters Target
        # Use fresh config from DataManager if available, fallback to passed novel_config
        setting = self.data_manager.get_setting()
        config = setting.get("config", {})
        
        target_words_wan = config.get("total_words_wan")
        if target_words_wan is None:
             target_words_wan = novel_config.get("total_words_wan", 20)
             
        # Check config first, then root
        chapter_words = config.get("chapter_words")
        if not chapter_words:
            chapter_words = setting.get("chapter_words", 3000)
        
        calculated_limit = int((target_words_wan * 10000) / chapter_words)
        
        # 2. Override limit if explicitly set in config
        total_chapters = novel_config.get("chapter_limit", calculated_limit)
        
        # 3. Fallback to pacing guide structure
        pacing_guide = setting.get("pacing_guide", {})
        
        # Fix: Handle case where pacing_guide is a list (direct structure)
        if isinstance(pacing_guide, list):
            pacing_guide = {"structure": pacing_guide}
            
        if isinstance(pacing_guide, dict):
            if pacing_guide.get("total_chapters"):
                 total_chapters = int(pacing_guide.get("total_chapters"))
            elif "structure" in pacing_guide and isinstance(pacing_guide["structure"], list) and pacing_guide["structure"]:
                 last_item = pacing_guide["structure"][-1]
                 if not novel_config.get("chapter_limit"): 
                     if "chapter_end" in last_item: # Volume structure
                         total_chapters = last_item.get("chapter_end", total_chapters)
                     elif "chapter_id" in last_item: # Flat structure
                         total_chapters = len(pacing_guide["structure"])
        
        limit = max(total_chapters, 5)
        remaining = max(0, limit - current_chapter)
        progress = current_chapter / limit if limit > 0 else 0
        
        stage = "未知阶段"
        if progress < 0.2:
            stage = "铺垫期 (0-20%)"
        elif progress < 0.5:
            stage = "发展期 (20-50%)"
        elif progress < 0.8:
            stage = "高潮期 (50-80%)"
        else:
            stage = "收尾期 (80-100%)"
            
        return {
            "total": limit,
            "current": current_chapter,
            "remaining": remaining,
            "stage": stage,
            "progress": progress
        }

    def generate_chapter_brief(self, context_text, chap_num, novel_type, pacing_status):
        """Generate a pre-write brief for the upcoming chapter."""
        history = self.data_manager.get_history()
        history_context = f"【历史背景】\n{history.get('rolling_summary', '')}\n\n"
        recent_chapters = json.dumps(history.get('chapters', []), ensure_ascii=False, indent=2)
        history_context += f"【最近章节摘要】\n{recent_chapters}"
        
        if novel_type == "short":
             type_str = "短篇小说 (无分卷)"
             target_str = f"全书目标 {pacing_status['total']} 章"
        else:
             type_str = "长篇小说"
             target_str = f"当前目标 {pacing_status['total']} 章 (动态调整)"

        # --- New: Detailed Pacing Analysis (Disabled based on User Request) ---
        # User requested to remove the "Rhythm Analysis Report" feature (Terminal Output).
        # We also skip the LLM call to save time and tokens, since the user doesn't want to see it.
        # We will use a simplified placeholder for the writer's brief.
        
        formatted_suggestion = "（用户已禁用节奏分析报告）"
        sug = {}
            
        # Display Pacing Analysis to User - DISABLED
        # self.console.print(Panel(formatted_suggestion.strip(), title="📊 节奏分析报告", style="cyan"))

        pacing_info = f"""【剧情节奏数据】
- 小说类型：{type_str}
- 章节进度：第 {pacing_status['current']} 章 / {target_str}
- 剩余章节：约 {pacing_status['remaining']} 章
- 当前阶段：{pacing_status['stage']}
- 总体进度：{int(pacing_status.get('progress', 0) * 100)}%
"""
        
        messages = [
            {"role": "system", "content": prompt_config.CHAPTER_BRIEF_SYSTEM.content},
            {"role": "user", "content": f"【当前任务】请为 **第 {chap_num} 章** 生成创作简报。\n\n{pacing_info}\n\n{context_text}\n\n{history_context}"}
        ]
        
        brief = self.chat(messages, description=f"正在生成第 {chap_num} 章创作简报...")
        self.console.print(Panel(Markdown(brief), title=f"📋 第 {chap_num} 章创作简报 (Anti-Drift Check)"))
        return brief

    def compress_history(self, context_manager, settings_text):
        """Compress old chapters into rolling summary based on context manager."""
        history = self.data_manager.get_history()
        
        if not context_manager.should_compress(settings_text, history):
            return

        chapters = history.get("chapters", [])
        keep_count = context_manager.calculate_keep_count(settings_text, history)
        
        if len(chapters) <= keep_count:
            return
            
        to_compress = chapters[:-keep_count]
        keep_active = chapters[-keep_count:]
        
        self.console.print(Panel(f"正在压缩前 {len(to_compress)} 章剧情 (保留最后 {keep_count} 章)...", style="bold blue"))
        
        compress_input = json.dumps(to_compress, ensure_ascii=False, indent=2)
        current_summary = history.get("rolling_summary", "")
        
        messages = [
            {"role": "system", "content": prompt_config.STORY_COMPRESSION_SYSTEM.content},
            {"role": "user", "content": f"【当前历史背景】\n{current_summary}\n\n【待压缩章节】\n{compress_input}"}
        ]
        
        new_rolling_summary = self.chat(messages, description="剧情压缩中...")
        
        if new_rolling_summary and "Error" not in new_rolling_summary:
            self.data_manager.update_history({
                "rolling_summary": new_rolling_summary,
                "chapters": keep_active
            })
            self.console.print("[green]✅ 剧情压缩完成，记忆库已更新。[/green]")

    def evolve_author_style(self):
        """Analyze recent chapters to update author style."""
        history = self.data_manager.get_history()
        recent_chapters = history.get("chapters", [])[-3:]
        if not recent_chapters: return

        self.console.print("[magenta]正在分析作者近期风格演变...[/magenta]")
        
        content_sample = json.dumps([c.get("summary", "") for c in recent_chapters], ensure_ascii=False)
        author = self.data_manager.get_author()
        
        current_style = "暂无"
        if "style_analysis" in author and isinstance(author["style_analysis"], dict):
             current_style = author["style_analysis"].get("description_style", "暂无")
        elif "style_description" in author:
             current_style = author["style_description"]

        messages = [
            {"role": "system", "content": prompt_config.AUTHOR_STYLE_ANALYZER_SYSTEM.content},
            {"role": "user", "content": f"【最近章节摘要】\n{content_sample}\n\n【当前风格】\n{current_style}"}
        ]
        
        new_style = self.chat(messages, description="风格提炼中...")
        if new_style and "Error" not in new_style:
            self.data_manager.update_author({
                "style_analysis": {"description_style": new_style}
            })
            self.console.print(Panel(Markdown(new_style), title="🎭 作者风格已进化"))

    def check_life_event(self):
        """Check for random life events affecting the author."""
        import random
        author_config = self.data_manager.get_author().get("config", {})
        if not author_config.get("enable_life_events", True):
            return None

        if random.random() < 0.05: # 5% chance
            messages = [{"role": "system", "content": prompt_config.LIFE_EVENT_GENERATOR_SYSTEM.content}]
            res = self.chat(messages, description="检测现实波动...")
            
            event_data = self.parse_json_safe(res)
            if event_data:
                self.console.print(Panel(f"[bold]{event_data['event']}[/bold]\n影响: {event_data['effect']}", title="⚡️ 作者现实生活发生波动", style="yellow"))
                
                evolution = self.data_manager.get_author().get("evolution", [])
                evolution.append({
                    "timestamp": time.time(),
                    "event": event_data['event'],
                    "effect": event_data['effect']
                })
                self.data_manager.update_author({"evolution": evolution})
                return event_data
        return None
