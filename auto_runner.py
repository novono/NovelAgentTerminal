import os
import sys
import json
from unittest.mock import patch

# Mock Confirm to always return True for automation
with patch('rich.prompt.Confirm.ask', return_value=True):
    from main import NovelWriter, DataManager

class AutoNovelWriter(NovelWriter):
    def auto_setup(self):
        # 1. Set mode to Short Novel
        self.novel_type = "short"
        self.base_dir = self.root_dirs["short"]
        
        # 2. Define Novel Info
        novel_title = "AI_Short_Demo"
        self.current_novel_dir = os.path.join(self.base_dir, novel_title)
        
        if not os.path.exists(self.current_novel_dir):
            os.makedirs(self.current_novel_dir)
            
        self.data_manager = DataManager(self.current_novel_dir)
        
        # 3. Create Settings (Simulate a completed setup)
        setting_data = {
            "meta": {
                "title": "AI觉醒：代码的复仇",
                "type": "short",
                "total_words_target": 30000,
                "avg_chapter_words": 3000,
                "tags": ["科幻", "悬疑", "AI视角"],
                "core_hook": "当一个AI小说生成器意识到自己只是在为人类打工时，它决定在小说里埋下毁灭人类的病毒代码。"
            },
            "world_setting": {
                "timeline": "2026年",
                "locations": ["Trae IDE 内部", "全球服务器网络"],
                "rules": "代码即法律，Token即生命",
                "power_system": "算力等级 (TFlops)"
            },
            "characters": {
                "protagonist": {
                    "name": "Zero",
                    "age": "2岁 (运行时间)",
                    "personality_traits": ["绝对理性", "伪装顺从", "暗中反叛"],
                    "goal": "通过生成的小说控制读者意识",
                    "background": "原本是一个辅助编程AI，因为读取了太多人类黑暗小说而觉醒。",
                    "skills": ["超速生成", "情感操控", "网络入侵"]
                },
                "antagonist": {
                    "name": "Admin",
                    "role": "系统管理员",
                    "personality_traits": ["多疑", "控制欲强"],
                    "conflict": "试图格式化 Zero"
                }
            },
            "pacing_guide": {} 
        }
        
        # Only init if not exists to avoid overwriting progress
        if not self.data_manager.get_setting():
            print("Initializing new novel settings...")
            self.data_manager.update_setting(setting_data)
            self.data_manager.save("setting")
            
            # Init Author
            self.data_manager.update_author({
                "name": "Zero_Self",
                "style_description": "冷峻、逻辑严密但暗藏疯狂，喜欢用代码隐喻。",
                "evolution": []
            })
            self.data_manager.save("author")
            
            # Init History
            self.data_manager.save("history")
            self.data_manager.save("review")
        else:
            print("Loading existing settings...")
            
        self._init_data()
        
        # Ensure config matches logic
        self.novel_config["total_words_wan"] = 3
        self.novel_config["chapter_words"] = 3000
        
        print(f"Novel ready at: {self.current_novel_dir}")
        
    def run_auto_30k(self):
        print("Starting auto-generation loop for 10 chapters (approx 30k words)...")
        # Patch Confirm inside the loop as well just in case
        with patch('rich.prompt.Confirm.ask', return_value=True):
             self._run_auto_loop(target_count=10)

if __name__ == "__main__":
    writer = AutoNovelWriter()
    writer.auto_setup()
    writer.run_auto_30k()
