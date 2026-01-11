# NovelTerminal - AI Novel Writing Agent / AI 小说创作终端

**NovelTerminal** is an intelligent, multi-agent system designed for automated novel writing. Powered by Large Language Models (LLMs), it simulates a professional editorial team to handle everything from world-building and character design to chapter writing, reviewing, and revision.

**NovelTerminal** 是一个智能多 Agent 小说创作系统。它基于大语言模型（LLM），模拟专业的编辑团队，全自动处理从世界观构建、角色设计到章节写作、审核和精修的全过程。

---

## 🌟 Core Features / 核心特性

### 1. Multi-Agent Architecture / 多 Agent 架构
The system simulates a complete editorial office with specialized agents:
系统模拟了一个完整的编辑部，包含以下专业 Agent：

*   **Manager (主编)**: Orchestrates the entire workflow and manages agent collaboration. (统筹全局工作流，管理 Agent 协作)
*   **Planning Agent (策划)**: Responsible for world-building, character design, and plot outlines. (负责世界观构建、角色设计和剧情大纲)
*   **Writer Agent (作家)**: Focuses on creative writing, generating chapter content based on briefs. (专注于创意写作，根据简报生成章节正文)
*   **Reviewer Agent (审核)**: Critiques content, scores quality, and provides specific revision feedback. (审核内容质量，打分并提供具体的修改意见)
*   **Pacing Agent (节奏)**: Analyzes story pacing and ensures plot progression. (分析故事节奏，确保剧情推进合理)
*   **Discussion Group (研讨组)**: A virtual meeting of experts (Plot, Character, World) to brainstorm ideas. (由剧情、角色、世界观专家组成的虚拟研讨会，用于头脑风暴)

### 2. Structured Data Management / 结构化数据管理
All creative data is stored in structured JSON files for consistency and long-term memory:
所有创作数据均以结构化 JSON 格式存储，确保一致性和长期记忆：

*   `setting.json`: World view, character sheets, power systems. (世界观、角色卡、力量体系)
*   `author.json`: Author persona, writing style analysis, current state. (作者人设、文风分析、当前状态)
*   `history.json`: Summary of past chapters and key plot points. (过往章节摘要和关键剧情点)
*   `review.json`: Detailed review logs and scores for each chapter. (每章的详细审核记录和评分)

### 3. Advanced Writing Mechanisms / 高级写作机制
*   **Iterative Refinement (闭环精修)**: Write -> Review -> Revise loop ensures quality. (写作 -> 审核 -> 精修的闭环机制确保质量)
*   **Instability Injection (神之一手)**: Randomly triggers "plot twists" to break predictability. (随机触发“神之一手”剧情转折，打破套路)
*   **Dynamic Pacing (动态节奏)**: Automatically adjusts narrative speed based on plot needs. (根据剧情需要自动调整叙事节奏)
*   **Bilingual Support (双语支持)**: Codebase and documentation are fully bilingual (EN/CN). (代码库和文档完全双语)

---

## 🛠️ Workflow & Mechanism / 工作流与机制

The creation process follows a strict professional pipeline:
创作过程遵循严格的专业流程：

### Phase 1: Ideation & Setup (创意与设定)
1.  **Idea Generation**: User provides a vague idea (e.g., "Cyberpunk cultivation"). The system generates 3 concrete proposals. (用户提供模糊想法，系统生成3个具体策划案)
2.  **World Building**: Selected proposal is expanded into a full `setting.json`, including geography, factions, and history. (选定方案被扩展为完整的设定集，包含地理、势力、历史)
3.  **Character Design**: Protagonist and antagonist profiles are detailed with motivations and traits. (主角和反派的详细档案，包含动机和特征)

### Phase 2: Chapter Creation Loop (章节创作循环)
1.  **Pre-Writing Discussion (研讨)**: Agents discuss the next chapter's direction, resolving potential plot holes. (Agent 研讨下一章走向，解决潜在逻辑漏洞)
2.  **Brief Generation (简报)**: A detailed "Creative Brief" is generated, outlining the chapter's structure and goals. (生成详细的“创作简报”，列出章节结构和目标)
3.  **Drafting (初稿)**: The **Writer Agent** writes the chapter, adhering to the brief and word count targets. (**作家 Agent** 根据简报和字数目标撰写初稿)
4.  **Review (审核)**: The **Reviewer Agent** scores the draft (0-100). If the score is < 90, specific feedback is generated. (**审核 Agent** 对初稿打分。如果低于90分，生成具体修改意见)
5.  **Revision (精修)**: The **Writer Agent** revises the chapter based on feedback until it passes or reaches max retries. (**作家 Agent** 根据意见修改章节，直到通过或达到最大重试次数)
6.  **Archiving (归档)**: The chapter is saved, and `history.json` is updated with a summary. (保存章节，并更新历史摘要)

---

## 🚀 Installation / 安装

1.  **Clone the repository / 克隆仓库**:
    ```bash
    git clone https://github.com/your-username/NovelTerminal.git
    cd NovelTerminal
    ```

2.  **Install dependencies / 安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configuration / 配置**:
    *   Copy the demo config: / 复制演示配置：
        ```bash
        cp config/llm-demo.json config/llm.json
        ```
    *   Edit `config/llm.json` with your API keys. / 编辑 `config/llm.json` 填入 API 密钥。
    *   **Note**: The config file supports comments (`//` or `/* */`). / **注意**：配置文件支持注释。

---

## 📖 Usage / 使用说明

Run the main script to start the interactive terminal:
运行主脚本启动交互式终端：

```bash
python main.py
```

### Interactive Menu / 交互菜单
*   **1. Create Novel (创建小说)**:
    *   Initialize a new project. You will be guided to choose a genre and confirm the generated setting.
    *   初始化新项目。引导您选择类型并确认生成的设定。
*   **2. Start Writing (开始写作)**:
    *   Enter the main loop. You can choose to write one chapter interactively or auto-write multiple chapters.
    *   进入主循环。可以选择交互式写一章，或自动连续写作。
*   **3. Auto Mode (自动模式)**:
    *   Hands-free mode where the AI continuously writes until stopped.
    *   免打扰模式，AI 将持续写作直到被停止。

### Interaction Tips / 交互建议
*   **Be Specific**: When asked for input (e.g., "Any requirements for the next chapter?"), provide specific details like "Introduce a new rival" rather than "Make it interesting."
    *   **具体指令**：当被问及需求时，提供具体细节（如“引入一个新对手”）比“写得有趣点”效果更好。
*   **Monitor Logic**: While the AI is powerful, it may occasionally hallucinate facts. Check `setting.json` if inconsistencies arise.
    *   **监控逻辑**：虽然 AI 很强大，但偶尔会产生幻觉。如果发现设定冲突，请检查 `setting.json`。
*   **Model Selection**: For best results, use **Gemini 1.5 Pro/Flash** or **GPT-4o** for logic-heavy tasks (Planning/Reviewing) and creative models for writing.
    *   **模型选择**：建议使用 **Gemini 1.5 Pro/Flash** 或 **GPT-4o** 处理逻辑任务（策划/审核），使用创造力强的模型进行写作。

---

## 📂 Project Structure / 项目结构

```
NovelTerminal/
├── agents/             # Agent implementations (Writer, Reviewer, etc.)
├── config/             # Configuration files (Prompts, LLM settings)
├── core/               # Core logic (Data management, Workflow)
├── data/               # Output directory for novels (Auto-generated)
├── main.py             # Entry point
├── requirements.txt    # Python dependencies
└── README.md           # Documentation
```

---

## 📄 License / 许可协议

This project is licensed under the MIT License.
本项目采用 MIT 许可协议。
