from typing import List, Dict, Optional, Any
import json
import os
import time
from typing import List, Dict, Optional, Any
from rich.console import Console
from rich.markdown import Markdown
from config.llm_config import llm_client
import re

console = Console()

class DataManager:
    """
    Manages the 4 core JSON files: setting.json, author.json, history.json, review.json.
    Ensures atomic updates, data consistency, hot-reloading, and auto-repair.
    """
    def __init__(self, novel_dir: str, enable_auto_repair: bool = True):
        self.novel_dir = novel_dir
        self.enable_auto_repair = enable_auto_repair
        self.files = {
            "setting": os.path.join(novel_dir, "setting.json"),
            "author": os.path.join(novel_dir, "author.json"),
            "history": os.path.join(novel_dir, "history.json"),
            "review": os.path.join(novel_dir, "review.json")
        }
        self.data = {
            "setting": {},
            "author": {"traits": {}, "style_analysis": {}, "evolution": [], "config": {"enable_instability": False, "enable_life_events": False}},
            "history": {"status": {}, "characters": {}, "foreshadowing": [], "chapters": [], "rolling_summary": ""},
            "review": {"reviews": [], "audience_profile": {}, "suggestions_track": []}
        }
        self._mtimes = {}  # Cache for file modification times
        
        if self.enable_auto_repair:
            self._load_all()

    def _load_all(self):
        """Initial load of all files."""
        for key in self.files:
            self._load_file(key)

    def _load_file(self, key: str, force: bool = False):
        """
        Loads a file with caching and hot-reload support.
        If file is missing or corrupt, attempts LLM-based repair.
        """
        path = self.files[key]
        
        # 1. Handle Missing File
        if not os.path.exists(path):
            if self.enable_auto_repair:
                if self._repair_missing_file(key):
                    # If repair created the file, proceed to load
                    pass
                else:
                    # If repair failed or not possible, ensure default structure exists in memory
                    if key not in self.data or not self.data[key]:
                        # self.data already has defaults from __init__, just warn
                        console.print(f"[yellow]Warning: {key}.json not found and repair skipped. Using defaults.[/yellow]")
                    return
            else:
                return

        # 2. Check for Hot Reload (Mtime)
        try:
            current_mtime = os.path.getmtime(path)
            if not force and key in self._mtimes and current_mtime == self._mtimes[key]:
                return  # Cache hit
        except OSError:
            pass # File might have been deleted/moved in the split second

        # 3. Load & Parse
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                if not content.strip():
                    raise ValueError("Empty file")
                
                loaded = json.loads(content)
                if loaded:
                    self.data[key] = loaded
                    self._mtimes[key] = current_mtime
                    
                    # Ensure default config exists for author
                    if key == "author" and "config" not in self.data["author"]:
                        self.data["author"]["config"] = {"enable_instability": False, "enable_life_events": False}
                        
        except (json.JSONDecodeError, ValueError) as e:
            console.print(f"[red]Error loading {key}.json: {e}. Attempting auto-repair...[/red]")
            if self._repair_corrupt_file(key, content if 'content' in locals() else ""):
                # Retry load recursively (force=True to bypass mtime check if file just written)
                self._load_file(key, force=True)

    def _repair_missing_file(self, key: str) -> bool:
        """Attempts to create a missing file using LLM or defaults."""
        console.print(f"[cyan]检测到 {key}.json 缺失，正在尝试自动补全...[/cyan]")
        
        # Simple default templates
        defaults = {
            "setting": {
                "meta": {"title": os.path.basename(self.novel_dir), "tags": [], "total_words_target": "20万"},
                "chapter_words": 2000,
                "world_setting": {},
                "characters": {"protagonist": {}, "antagonist": {}, "supporting": []}
            },
            "author": {"traits": {}, "config": {"enable_instability": False}},
            "history": {"chapters": [], "rolling_summary": ""},
            "review": {"reviews": []}
        }
        
        # If we have some context (e.g. creating setting from nothing), we could ask LLM.
        # For now, writing a valid skeleton is safer and faster.
        # User requirement says "LLM自动补全", let's try LLM for 'setting' if it's missing,
        # using directory name as hint.
        
        if key == "setting":
            try:
                novel_name = os.path.basename(self.novel_dir)
                prompt = f"请为一个名为《{novel_name}》的小说生成一个标准的 setting.json 配置文件模板。只返回 JSON 内容，不要Markdown格式。"
                messages = [{"role": "user", "content": prompt}]
                response = llm_client.chat_author(messages)
                cleaned = self._clean_json(response)
                data = json.loads(cleaned)
                # Ensure critical fields
                if "chapter_words" not in data: data["chapter_words"] = 2000
                
                self.data[key] = data
                self.save(key)
                console.print(f"[green]已通过 LLM 自动生成 {key}.json[/green]")
                return True
            except Exception as e:
                console.print(f"[red]LLM 生成失败: {e}，使用默认模板。[/red]")
        
        # Fallback to defaults
        if key in defaults:
            self.data[key] = defaults[key]
            self.save(key)
            console.print(f"[green]已创建默认 {key}.json[/green]")
            return True
            
        return False

    def _repair_corrupt_file(self, key: str, content: str) -> bool:
        """Attempts to fix corrupt JSON using LLM."""
        console.print(f"[cyan]正在尝试修复 {key}.json 格式错误...[/cyan]")
        try:
            prompt = f"以下是一个损坏的 JSON 文件内容，请修复它并返回合法的 JSON。不要改变数据结构和键值，只修复语法错误。\n\n{content[:2000]}" # Limit context
            messages = [{"role": "user", "content": prompt}]
            response = llm_client.chat_author(messages)
            cleaned = self._clean_json(response)
            data = json.loads(cleaned)
            
            self.data[key] = data
            self.save(key)
            console.print(f"[green]成功修复 {key}.json[/green]")
            return True
        except Exception as e:
            console.print(f"[red]自动修复失败: {e}[/red]")
            return False

    def _clean_json(self, text: str) -> str:
        """Helper to extract JSON from text."""
        match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if match:
            return match.group(1)
        match = re.search(r'```\s*([\s\S]*?)\s*```', text)
        if match:
            return match.group(1)
        return text.strip()

    def save(self, key: str):
        if key not in self.files: return
        path = self.files[key]
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.data[key], f, ensure_ascii=False, indent=2)
        except Exception as e:
            console.print(f"[red]Error saving {key}.json: {e}[/red]")

    # --- Accessors & Updaters ---

    def get_config_value(self, key_path: str, default: Any = None) -> Any:
        """
        Unified interface for accessing configuration values.
        key_path format: "filename.key1.key2" (e.g., "setting.chapter_words")
        """
        parts = key_path.split(".")
        if not parts:
            return default
            
        file_key = parts[0]
        if file_key not in self.files:
            return default
            
        # Trigger hot reload for this file
        self._load_file(file_key)
        
        value = self.data.get(file_key, {})
        for part in parts[1:]:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return default
                
        return value if value is not None else default

    def get_setting(self) -> Dict:
        self._load_file("setting")
        return self.data["setting"]

    def update_setting(self, updates: Dict):
        self._load_file("setting") # Ensure we have latest before update
        self._deep_update(self.data["setting"], updates)
        self.save("setting")

    def get_author(self) -> Dict:
        self._load_file("author")
        return self.data["author"]

    def update_author(self, updates: Dict):
        self._load_file("author")
        self._deep_update(self.data["author"], updates)
        self.save("author")
        
    def get_history(self) -> Dict:
        self._load_file("history")
        return self.data["history"]

    def update_history(self, updates: Dict):
        self._load_file("history")
        self._deep_update(self.data["history"], updates)
        self.save("history")

    def add_chapter_history(self, chapter_data: Dict):
        self._load_file("history")
        if "chapters" not in self.data["history"]:
            self.data["history"]["chapters"] = []
        self.data["history"]["chapters"].append(chapter_data)
        self.save("history")

    def get_review(self) -> Dict:
        self._load_file("review")
        return self.data["review"]

    def add_review(self, review_data: Dict):
        self._load_file("review")
        if "reviews" not in self.data["review"]:
            self.data["review"]["reviews"] = []
        self.data["review"]["reviews"].append(review_data)
        self.save("review")

    def save_chapter_text(self, chapter_num: int, content: str, title: str = None):
        """Saves the chapter content to a text file."""
        chapters_dir = os.path.join(self.novel_dir, "chapters")
        if not os.path.exists(chapters_dir):
            os.makedirs(chapters_dir)
            
        if title:
            # Sanitize title for filename
            safe_title = re.sub(r'[\\/*?:"<>|]', "", title).strip()
            filename = f"第{chapter_num}章_{safe_title}.txt"
        else:
            filename = f"Chapter_{chapter_num}.txt"

        path = os.path.join(chapters_dir, filename)
        
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            console.print(f"[green]已保存章节文件: {filename}[/green]")
        except Exception as e:
            console.print(f"[red]保存章节文件失败: {e}[/red]")

    def _deep_update(self, target, updates):
        for k, v in updates.items():
            if isinstance(v, dict) and k in target and isinstance(target[k], dict):
                self._deep_update(target[k], v)
            else:
                target[k] = v

    def generate_markdown_setting(self) -> str:
        """Convert setting.json to human-readable Markdown for LLM context."""
        s = self.data["setting"]
        if not s: return "暂无设定"
        
        meta = s.get("meta", {})
        wv = s.get("world_view", s.get("world_setting", {})) # Compatible with both keys
        chars = s.get("characters", {})
        
        md = f"# {meta.get('title', '未命名小说')}\n\n"
        md += f"## 1. 基础信息\n"
        md += f"* **核心卖点**: {meta.get('core_hook', '无')}\n"
        md += f"* **主题**: {meta.get('theme', '无')}\n"
        md += f"* **预期字数**: {meta.get('estimated_word_count', meta.get('total_words_target', '未设置'))}\n"
        
        tags = meta.get('tags', [])
        if isinstance(tags, list):
            md += f"* **标签**: {', '.join(tags)}\n\n"
        else:
            md += f"* **标签**: {tags}\n\n"
        
        md += f"## 2. 世界观\n"
        md += f"* **背景**: {wv.get('background', '无')}\n"
        md += f"* **地理/场景**: {wv.get('geography', wv.get('locations', '无'))}\n"
        md += f"* **世界规则**: {wv.get('world_rules', wv.get('rules', '无'))}\n"
        
        power = wv.get('power_system', [])
        if isinstance(power, list):
            md += f"* **力量体系**: {'; '.join(power)}\n"
        else:
            md += f"* **力量体系**: {power}\n"
            
        factions = wv.get('factions', [])
        if factions:
            md += "* **势力**:\n"
            if isinstance(factions, list):
                for f in factions:
                    if isinstance(f, dict):
                        md += f"  - {f.get('name', '?')}: {f.get('description', '')}\n"
                    else:
                        md += f"  - {f}\n"
            else:
                md += f"  - {factions}\n"
        md += "\n"
        
        md += f"## 3. 角色\n"
        p = chars.get("protagonist", {})
        md += f"### 主角: {p.get('name', '未命名')}\n"
        md += f"* **年龄**: {p.get('age', '未知')}\n"
        md += f"* **外貌**: {p.get('appearance', '暂无描述')}\n"
        md += f"* **性格特征**: {p.get('personality', p.get('personality_traits', '暂无'))}\n"
        md += f"* **技能/金手指**: {p.get('gold_finger', p.get('skills', '无'))}\n"
        md += f"* **当前目标**: {p.get('goal', '无')}\n"
        
        # New relationships field at characters level
        rels = chars.get('relationships')
        if rels:
             md += f"* **人际关系网**: {rels}\n"
        
        # Old relationships field inside protagonist
        elif 'relationships' in p:
            md += "* **人际关系**:\n"
            for rel in p['relationships']:
                md += f"  - {rel.get('name', '?')} ({rel.get('relation', '?')}): {rel.get('attitude', '?')}\n"
        
        a = chars.get("antagonist", {})
        if a:
            md += f"\n### 反派: {a.get('name', '未命名')}\n"
            md += f"* **头衔**: {a.get('title', '')}\n"
            md += f"* **动机**: {a.get('motivation', '未知')}\n"
            md += f"* **背景**: {a.get('background', '')}\n"
        
        supporting = chars.get("supporting", [])
        if supporting:
            md += "\n### 配角:\n"
            for sup in supporting:
                name = sup.get('name', '未命名')
                role = sup.get('role', '路人')
                trait = sup.get('trait', '')
                md += f"* **{name}** ({role}): {trait}\n"
            
        return md
