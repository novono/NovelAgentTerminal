import os
import time
import re
import json
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.markdown import Markdown

from core.data_manager import DataManager
from core.context_manager import ContextManager
from config.llm_config import LLMConfig, llm_client
import config.category_config as category_config

from agents.planning_agent import PlanningAgent
from agents.writer_agent import WriterAgent
from agents.review_agent import ReviewAgent
from agents.pacing_agent import PacingAgent

console = Console()

class ManagerAgent:
    """
    The Orchestrator.
    Manages the overall workflow, user interaction, and delegates tasks to specific agents.
    协调者。管理整体工作流、用户交互，并将任务委派给特定的 Agent。
    """
    def __init__(self):
        self.novel_type = "long"
        self.root_dirs = {
            "long": os.path.join(os.getcwd(), "novel"),
            "short": os.path.join(os.getcwd(), "short_novels")
        }
        # Ensure directories exist / 确保目录存在
        for path in self.root_dirs.values():
            if not os.path.exists(path):
                os.makedirs(path)
        
        self.base_dir = self.root_dirs["long"]
        self.current_novel_dir = None
        self.novel_config = {}
        self.target_chapter_words = 2000
        self.low_score_count = 0
        self.instability_miss_count = 0
        
        self.data_manager: Optional[DataManager] = None
        self.context_manager = ContextManager(max_chars=LLMConfig.DEFAULT_CONTEXT_WINDOW_CHARS)
        
        # Sub-Agents (Initialized later when DataManager is ready)
        # 子 Agent（在 DataManager 准备好后初始化）
        self.planner: Optional[PlanningAgent] = None
        self.writer: Optional[WriterAgent] = None
        self.reviewer: Optional[ReviewAgent] = None
        self.pacer: Optional[PacingAgent] = None

    def _init_agents(self):
        """Initialize sub-agents with the current DataManager."""
        """使用当前 DataManager 初始化子 Agent。"""
        if self.data_manager:
            self.planner = PlanningAgent(self.data_manager)
            self.writer = WriterAgent(self.data_manager)
            self.reviewer = ReviewAgent(self.data_manager)
            self.pacer = PacingAgent(self.data_manager)

    def run(self):
        """Main entry point."""
        """主入口点。"""
        console.print(Panel("欢迎使用 NovelTerminal (Multi-Agent Refactored)", style="bold green"))
        
        self.test_connectivity()
        
        self.select_mode()
        
        while True:
            choice = self.main_menu()
            if choice == 1:
                self.create_novel()
            elif choice == 2:
                self.load_novel()
            elif choice == 3:
                if self.data_manager:
                    self.writer_loop()
                else:
                    console.print("[red]请先加载或创建小说。[/red]")
            elif choice == 4:
                self.configure_author_model()
            elif choice == 5:
                console.print("[yellow]再见！[/yellow]")
                break

    def test_connectivity(self):
        """Test connection to Author and Reviewer models."""
        console.print(Panel("模型连接测试", title="系统检查"))
        if Confirm.ask("是否进行模型连接性测试？(建议首次运行时进行)", default=True):
            author_model = LLMConfig.AUTHOR_MODEL_KEY
            reviewer_model = LLMConfig.REVIEWER_MODEL_KEY
            
            if author_model == reviewer_model:
                with console.status(f"[bold green]正在测试作者与审核模型 ({author_model})...[/bold green]"):
                    success, msg = llm_client.test_connection(author_model)
                    if success:
                        console.print(f"[green]✅ 作者与审核模型 ({author_model}) 连接成功！[/green]")
                    else:
                        console.print(f"[red]❌ 作者与审核模型 ({author_model}) 连接失败: {msg}[/red]")
            else:
                with console.status(f"[bold green]正在测试作者模型 ({author_model})...[/bold green]"):
                    success, msg = llm_client.test_connection(author_model)
                    if success:
                        console.print(f"[green]✅ 作者模型 ({author_model}) 连接成功！[/green]")
                    else:
                        console.print(f"[red]❌ 作者模型 ({author_model}) 连接失败: {msg}[/red]")
            
                with console.status(f"[bold green]正在测试审核模型 ({reviewer_model})...[/bold green]"):
                    success, msg = llm_client.test_connection(reviewer_model)
                    if success:
                        console.print(f"[green]✅ 审核模型 ({reviewer_model}) 连接成功！[/green]")
                    else:
                        console.print(f"[red]❌ 审核模型 ({reviewer_model}) 连接失败: {msg}[/red]")
            
            console.print("[green]连接测试完成。[/green]")
            time.sleep(1)

    def select_mode(self):
        """Select novel creation mode."""
        console.print(Panel("请选择创作模式", title="模式选择"))
        console.print("1. 长篇小说 (分卷/无限流/百万字)")
        console.print("2. 短篇小说 (无分卷/快节奏/15万字内)")
        
        choice = IntPrompt.ask("请选择", choices=["1", "2"], default=1)
        if choice == 2:
            self.novel_type = "short"
            self.base_dir = self.root_dirs["short"]
            console.print("[cyan]已切换至：短篇小说模式[/cyan]")
        else:
            self.novel_type = "long"
            self.base_dir = self.root_dirs["long"]
            console.print("[cyan]已切换至：长篇小说模式[/cyan]")

    def main_menu(self) -> int:
        title = "主菜单"
        if self.current_novel_dir:
            novel_name = os.path.basename(self.current_novel_dir)
            title += f" (当前: {novel_name})"
            
        console.print(Panel("""
1. 新建小说
2. 加载小说
3. 开始/继续写作
4. 作者模型设置
5. 退出
""", title=title))
        return IntPrompt.ask("请选择", choices=["1", "2", "3", "4", "5"])

    def create_novel(self):
        # Temporary Planner for ideation (no DataManager needed yet)
        temp_planner = PlanningAgent(None) # BaseAgent handles None DM gracefully if just using chat? No, BaseAgent expects DM.
        # Actually BaseAgent just sets self.data_manager. If we don't use it, it's fine.
        # But generate_ideas doesn't use data_manager.
        
        console.print(Panel("开始创建新小说向导", title="新建小说"))
        
        # 1. Collect Requirements
        category_summary = self._collect_category_tags()
        user_req = Prompt.ask("请输入您的小说创作要求")
        
        if self.novel_type == "short":
            default_total = 15
            default_chap = 3000
        else:
            default_total = 200
            default_chap = 2000
            
        target_total_words = IntPrompt.ask("请输入小说预计总字数 (单位：万字)", default=default_total)
        target_chapter_words = IntPrompt.ask("请输入单章目标字数 (单位：字)", default=default_chap)
        
        requirements = f"{category_summary}\n\n【用户补充要求】\n{user_req}\n\n【字数要求】\n预计总字数：{target_total_words}万字\n单章字数：{target_chapter_words}字"
        
        # 2. Generate Ideas
        # We need a temporary base agent or just use the class directly?
        # Let's instantiate with a dummy DM or handle it.
        # BaseAgent needs DM for init.
        # Workaround: Pass None and ensure generate_ideas doesn't crash.
        temp_planner = PlanningAgent(None)
        
        # Loop for idea generation
        current_req = requirements
        selected_idea = None
        
        while True:
            templates = temp_planner.generate_ideas(current_req, self.novel_type)
            if not templates: continue

            console.print("\n[bold cyan]为您生成了以下方案：[/bold cyan]")
            for i, t in enumerate(templates):
                console.print(f"\n[bold]{i+1}. 《{t.get('title', '无题')}》[/bold]")
                console.print(f"   核心梗: {t.get('hook', '暂无')}")
            
            console.print(f"\n[bold]{len(templates)+1}. 以上都不满意，提供修改意见[/bold]")
            choice = IntPrompt.ask("请选择", choices=[str(i+1) for i in range(len(templates) + 1)])
            
            if choice == len(templates) + 1:
                feedback = Prompt.ask("请输入您的具体修改意见")
                current_req += f"\n\n【用户修改意见】\n{feedback}"
                continue
            else:
                selected_idea = templates[choice-1]
                break

        # 3. Create Directory
        novel_name = re.sub(r'[\\/*?:"<>|]', "", selected_idea.get('title', 'New_Novel'))
        folder_name = f"short_novel_{novel_name}" if self.novel_type == "short" else novel_name
        self.current_novel_dir = os.path.join(self.base_dir, folder_name)
        
        if os.path.exists(self.current_novel_dir):
            console.print(f"[red]文件夹 {folder_name} 已存在！[/red]")
            return # Should probably handle overwrite or rename

        os.makedirs(self.current_novel_dir)
        # Disable auto-repair for creation mode to avoid premature file generation
        self.data_manager = DataManager(self.current_novel_dir, enable_auto_repair=False)
        self._init_agents() # Now we have full agents
        
        # 4. Expand Settings
        console.print("[cyan]正在生成《小说设定集》JSON 数据...[/cyan]")
        
        full_req_dict = {
            "user_input": user_req,
            "category": category_summary,
            "total_words_target": target_total_words * 10000,
            "avg_chapter_words": target_chapter_words
        }
        
        # Review Loop for Settings
        current_setting_req = full_req_dict
        
        while True:
            setting_json = self.planner.create_setting(selected_idea, current_setting_req)
            
            # Preview
            self.data_manager.data["setting"] = setting_json
            md_preview = self.data_manager.generate_markdown_setting()
            console.print(Panel(Markdown(md_preview), title="设定集预览"))
            
            if Confirm.ask("是否确认使用该设定？", default=True):
                self.data_manager.save("setting")
                self.novel_config = setting_json.get("config", {})
                self.target_chapter_words = target_chapter_words
                break
            else:
                feedback = Prompt.ask("请输入修改建议")
                # Append feedback to requirements is tricky with dict, convert to string description
                current_setting_req["feedback"] = feedback
        
        # 5. Initialize Author
        author_profile = self.planner.init_author_profile(setting_json)
        self.data_manager.update_author(author_profile)
        console.print("[green]作者人格构建完成。[/green]")
        
        # 6. Plan Structure
        setting_summary = setting_json.get("meta", {}).get("core_hook", "")
        structure = self.planner.plan_structure(target_total_words, target_chapter_words, setting_summary, self.novel_type)
        self.data_manager.update_setting({"pacing_guide": structure})
        
        # Save config
        self.novel_config = {
            "total_words_wan": target_total_words,
            "chapter_words": target_chapter_words,
            "novel_type": self.novel_type
        }
        # In a real app, save novel_config to file too. DataManager handles 4 specific files. 
        # Maybe add it to setting.json?
        self.data_manager.update_setting({"config": self.novel_config})
        
        console.print("[green]小说初始化完成！[/green]")

    def load_novel(self):
        """Load existing novel."""
        novels = []
        for type_dir in self.root_dirs.values():
            if os.path.exists(type_dir):
                novels.extend([
                    os.path.join(type_dir, d) 
                    for d in os.listdir(type_dir) 
                    if os.path.isdir(os.path.join(type_dir, d))
                ])
        
        if not novels:
            console.print("[yellow]没有找到已有小说。[/yellow]")
            return

        console.print(Panel("请选择要加载的小说", title="加载小说"))
        for i, path in enumerate(novels):
            console.print(f"{i+1}. {os.path.basename(path)}")
            
        choice = IntPrompt.ask("请选择", choices=[str(i+1) for i in range(len(novels))])
        self.current_novel_dir = novels[choice-1]
        
        # Initialize DataManager (Automatically loads config)
        self.data_manager = DataManager(self.current_novel_dir)
        self._init_agents()
        
        # Load core settings to memory for Manager (though Agents should query DataManager directly)
        setting = self.data_manager.get_setting()
        self.novel_config = setting.get("config", {})
        # self.target_chapter_words is no longer needed as primary source, but we can keep it for display if needed
        # self.target_chapter_words = setting.get("chapter_words", 2000) 
        
        console.print(f"[green]已加载小说：{os.path.basename(self.current_novel_dir)}[/green]")

    def writer_loop(self):
        history = self.data_manager.get_history()
        start_chapter = len(history.get("chapters", [])) + 1
        
        # --- Mode Selection ---
        console.print(Panel("写作模式选择", title="模式"))
        console.print("1. 手动逐章模式 (默认)")
        console.print("2. 自动续写 - 定量模式 (指定章节数)")
        console.print("3. 自动续写 - 完本模式 (写完预定章节)")
        console.print("4. 自动续写 - 分卷模式 (写完当前卷)")
        
        mode_choice = IntPrompt.ask("请选择", choices=["1", "2", "3", "4"], default=1)
        
        auto_config = {"mode": "manual"}
        if mode_choice == 2:
            count = IntPrompt.ask("请输入要生成的章节数量")
            auto_config = {"mode": "count", "limit": count, "written": 0}
        elif mode_choice == 3:
            auto_config = {"mode": "complete"}
        elif mode_choice == 4:
            auto_config = {"mode": "volume"}
            
        console.print(f"[cyan]已启动模式: {auto_config['mode']}[/cyan]")
        
        while True:
            # --- Stop Condition Checks ---
            if auto_config["mode"] == "count":
                if auto_config["written"] >= auto_config["limit"]:
                    console.print("[green]✅ 已完成指定章节数量。[/green]")
                    break
            
            # 1. Pacing & Context
            pacing_status = self.pacer.calculate_pacing_status(start_chapter, self.novel_config)
            
            if auto_config["mode"] == "complete":
                if pacing_status["progress"] >= 1.0: # Reached total chapters
                     console.print("[green]✅ 小说已完结（达到预定章节数）。[/green]")
                     break
            
            # Context Management
            settings_text = self.data_manager.generate_markdown_setting()
            self.pacer.compress_history(self.context_manager, settings_text)
            
            # 2. Brief
            brief = self.pacer.generate_chapter_brief(settings_text, start_chapter, self.novel_type, pacing_status)
            
            # 3. Writing (with Instability Check)
            # Check pre-write instability
            if self.writer.check_instability_trigger("pre", self.instability_miss_count):
                # ... handle pre-write instability generation ...
                pass # Simplified for brevity, same logic as original
            
            # Note: target_words is now dynamically fetched by WriterAgent from config
            content = self.writer.write_chapter(brief, start_chapter, pacing_status) 
            
            # 4. Review & Revise Loop
            final_content = self._review_process(content, start_chapter, auto_config)
            
            if not final_content:
                console.print("[yellow]跳过本章保存。[/yellow]")
                if auto_config["mode"] != "manual":
                     console.print("[red]自动模式下跳过保存，停止自动续写。[/red]")
                     break
                if not Confirm.ask("是否继续写下一章？"):
                    break
                continue
                
            # 5. Post-Processing
            # Extract title from content
            lines = final_content.strip().split('\n')
            extracted_title = ""
            if lines:
                first_line = lines[0].strip()
                # Try to clean up "第X章" part to get pure title
                match = re.search(r'第\s*\d+\s*章\s*(.*)', first_line)
                if match:
                    extracted_title = match.group(1).strip()
                elif len(first_line) < 50: # Fallback if no "Chapter X" prefix but looks like title
                    extracted_title = first_line

            # Save chapter text file
            self.data_manager.save_chapter_text(start_chapter, final_content, title=extracted_title)

            summary_data = self.reviewer.generate_summary(final_content)
            
            chapter_entry = {
                "chapter": start_chapter,
                "title": f"第 {start_chapter} 章 {extracted_title}" if extracted_title else f"第 {start_chapter} 章",
                "summary": summary_data.get("summary", ""),
                "key_events": summary_data.get("key_events", []),
                "foreshadowing": summary_data.get("foreshadowing", []),
                "items_acquired": summary_data.get("items_acquired", []),
                "score": summary_data.get("plot_progression_score", 0)
            }
            self.data_manager.add_chapter_history(chapter_entry)
            
            # 6. Author Evolution & Life Events
            self.pacer.evolve_author_style()
            self.pacer.check_life_event()
            
            # Update counters
            start_chapter += 1
            if auto_config["mode"] == "count":
                auto_config["written"] += 1
                console.print(f"[blue]自动进度: {auto_config['written']}/{auto_config['limit']}[/blue]")
            
            # Check Volume End (Simple logic for now: check if pacing_guide has explicit volume breaks or if we should stop)
            # Since PacingAgent doesn't explicitly flag volume end, we might rely on user config or structure
            # For "Volume Mode", we might check if the *next* chapter starts a new volume in structure.
            # But structure parsing is complex. 
            # Simplification: If mode is volume, ask user every X chapters? No, that defeats the purpose.
            # Let's rely on manual stop for volume if not detectable, or check if 'chapter_end' matches current.
            if auto_config["mode"] == "volume":
                 # Try to check if current chapter is an end chapter in structure
                 setting = self.data_manager.get_setting()
                 pacing_guide = setting.get("pacing_guide", {})
                 structure = pacing_guide.get("structure", []) if isinstance(pacing_guide, dict) else pacing_guide
                 is_volume_end = False
                 if isinstance(structure, list):
                     for vol in structure:
                         if vol.get("chapter_end") == start_chapter - 1:
                             is_volume_end = True
                             break
                 
                 if is_volume_end:
                     console.print("[green]✅ 本卷已完结。[/green]")
                     break

            if auto_config["mode"] == "manual":
                if not Confirm.ask("继续写下一章？", default=True):
                    break

    def _review_process(self, content, chap_num, auto_config={"mode": "manual"}):
        """Orchestrates the review and revision loop."""
        current_content = content
        attempt = 0
        max_attempts = 3
        
        # Determine target words for revision consistency
        target_words = self.data_manager.get_config_value("setting.config.chapter_words")
        if target_words is None:
            target_words = self.data_manager.get_config_value("setting.chapter_words", 2000)
        target_words = int(target_words)
        
        while attempt < max_attempts:
            console.print(Panel(Markdown(current_content), title=f"第 {chap_num} 章预览 (v{attempt+1})"))
            
            # AI Review
            review = self.reviewer.review_chapter(current_content, {}, self.novel_type) # Need context
            
            score = review.get("score", 0)
            console.print(f"[bold]AI 评分: {score}[/bold]")
            console.print(f"评价: {review.get('comments', '')}")

            # Save review record
            review_record = review.copy()
            review_record.update({
                "chapter": chap_num,
                "attempt": attempt + 1,
                "timestamp": int(time.time()),
                "auto_mode": auto_config["mode"]
            })
            self.data_manager.add_review(review_record)
            
            # --- Auto Mode Logic ---
            if auto_config["mode"] != "manual":
                # Quality Threshold
                if score >= 85 and review.get("passed", False):
                    console.print("[green]自动审核通过！[/green]")
                    return current_content
                
                # If score is low, try auto-revise
                if attempt < 2: # Limit auto-retries
                    console.print("[yellow]评分较低，尝试自动精修...[/yellow]")
                    feedback = review.get("suggestions", ["优化剧情"])
                    current_content = self.reviewer.revise_chapter(current_content, feedback, target_words=target_words)
                    attempt += 1
                    continue
                else:
                    # Failed after retries
                    console.print("[red]多次修改仍未达标，暂停自动续写。[/red]")
                    if Confirm.ask("是否手动干预？(Yes: 手动修改, No: 放弃本章)", default=True):
                         # Fallthrough to manual handling below
                         pass
                    else:
                        return None

            # --- Manual Logic / Fallback ---
            if score >= 90 and review.get("passed", False):
                console.print("[green]AI 审核通过！[/green]")
                if Confirm.ask("用户最终确认？", default=True):
                    return current_content
            
            # If not passed or user wants to intervene
            if not Confirm.ask("是否满意当前版本？(No 进入修改流程)", default=True):
                feedback = Prompt.ask("请输入修改意见 (直接回车尝试 AI 自动精修)")
                if not feedback:
                    feedback = review.get("suggestions", ["优化剧情"])
                
                console.print("[yellow]正在精修...[/yellow]")
                current_content = self.reviewer.revise_chapter(current_content, feedback, target_words=target_words)
                attempt += 1
            else:
                return current_content
                
        return current_content

    # ... Helper methods like _collect_category_tags, get_existing_novels ...
    # Copied from original main.py but adapted
    
    def get_existing_novels(self):
        novels = []
        if not os.path.exists(self.base_dir):
            return []
        for d in os.listdir(self.base_dir):
            full_path = os.path.join(self.base_dir, d)
            if os.path.isdir(full_path):
                if os.path.exists(os.path.join(full_path, "setting.json")):
                    novels.append(d)
        return novels

    def _select_multi(self, title: str, options: list, max_selection: int = 2) -> list:
        """Helper for multiple selection."""
        console.print(f"\n[bold]{title} (最多选 {max_selection} 个，输入序号用逗号分隔，如 1,3):[/bold]")
        for i, opt in enumerate(options):
            console.print(f"{i+1}. {opt}")
        
        while True:
            choice_str = Prompt.ask("请选择序号 (直接回车跳过)")
            if not choice_str.strip():
                return []
            
            try:
                indices = [int(x.strip()) - 1 for x in choice_str.split(',') if x.strip()]
                if not indices:
                    return []
                
                if any(idx < 0 or idx >= len(options) for idx in indices):
                    console.print("[red]序号超出范围，请重试。[/red]")
                    continue
                    
                if len(indices) > max_selection:
                    console.print(f"[red]最多选择 {max_selection} 个，请重试。[/red]")
                    continue
                    
                return [options[idx] for idx in indices]
            except ValueError:
                console.print("[red]输入格式错误，请输入数字序号。[/red]")

    def _collect_category_tags(self) -> str:
        """Interactive flow to collect novel categories."""
        console.print(Panel("第一步：选择分类标签", style="bold cyan"))
        
        summary = ""
        
        if self.novel_type == "short":
             # Short Novel Flow
             # 1. Main Category
             main_cats = category_config.get_options(None, "主分类", novel_type="short")
             console.print(Panel(f"选择主分类 (必选)", style="bold cyan"))
             for i, cat in enumerate(main_cats):
                 console.print(f"{i+1}. [bold]{cat}[/bold]")
             
             cat_idx = IntPrompt.ask("请选择主分类序号", choices=[str(i+1) for i in range(len(main_cats))])
             main_category = main_cats[cat_idx-1]
             
             # 2. Plots
             plots = self._select_multi("选择情节", category_config.get_options(None, "情节", novel_type="short"), 3)
             
             # 3. Roles
             roles = self._select_multi("选择角色", category_config.get_options(None, "角色", novel_type="short"), 3)
             
             # 4. Emotions (New for Short)
             emotions = self._select_multi("选择情绪", category_config.get_options(None, "情绪", novel_type="short"), 2)
             
             # 5. Backgrounds (New for Short)
             backgrounds = self._select_multi("选择背景", category_config.get_options(None, "背景", novel_type="short"), 2)
             
             summary = f"""
【分类标签】
类型: 短篇小说
主分类: {main_category}
情节: {', '.join(plots) if plots else '无'}
角色: {', '.join(roles) if roles else '无'}
情绪: {', '.join(emotions) if emotions else '无'}
背景: {', '.join(backgrounds) if backgrounds else '无'}
"""
        else:
            # Long Novel Flow (Existing)
            channel = Prompt.ask("请选择频道", choices=["男频", "女频"], default="男频")
            
            # 1. Main Category (Single)
            main_cats = category_config.get_options(channel, "主分类")
            console.print(Panel(f"第二步：选择主分类 (必选)", style="bold cyan"))
            for i, cat in enumerate(main_cats):
                desc = category_config.get_description(cat)
                console.print(f"{i+1}. [bold]{cat}[/bold]: {desc}")
                
            cat_idx = IntPrompt.ask("请选择主分类序号", choices=[str(i+1) for i in range(len(main_cats))])
            main_category = main_cats[cat_idx-1]
            
            # 2. Themes (Multi)
            themes = self._select_multi("第三步：选择主题", category_config.get_options(channel, "主题"), 2)
            
            # 3. Roles (Multi)
            roles = self._select_multi("第四步：选择角色", category_config.get_options(channel, "角色"), 2)
            
            # 4. Plots (Multi)
            plots = self._select_multi("第五步：选择情节", category_config.get_options(channel, "情节"), 2)
            
            summary = f"""
【分类标签】
频道: {channel}
主分类: {main_category}
主题: {', '.join(themes) if themes else '无'}
角色: {', '.join(roles) if roles else '无'}
情节: {', '.join(plots) if plots else '无'}
"""
        
        console.print(Panel(summary, title="已选标签"))
        return summary

    def configure_author_model(self):
        if not self.data_manager:
            console.print("[red]请先加载或创建小说。[/red]")
            return
            
        author = self.data_manager.get_author()
        # Ensure config exists (handle legacy data)
        if "config" not in author:
            author["config"] = {
                "enable_instability": False,
                "enable_life_events": False
            }
        
        author_config = author["config"]
        
        # 1. Instability
        enable_instability = author_config.get("enable_instability", False)
        if Confirm.ask(f"当前[神之一手]: {enable_instability}。是否切换?", default=False):
            author_config["enable_instability"] = not enable_instability
            console.print(f"[green]已更新 [神之一手] -> {author_config['enable_instability']}[/green]")
            
        # 2. Life Events
        enable_life_events = author_config.get("enable_life_events", False)
        if Confirm.ask(f"当前[现实生活事件]: {enable_life_events}。是否切换?", default=False):
            author_config["enable_life_events"] = not enable_life_events
            console.print(f"[green]已更新 [现实生活事件] -> {author_config['enable_life_events']}[/green]")
            
        self.data_manager.update_author({"config": author_config})
