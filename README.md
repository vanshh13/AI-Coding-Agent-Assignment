# AI Coding Agent Assignment

A lightweight, token-efficient, and surgical AI coding assistant implemented in Python. Designed to iteratively explore a repository, formulate precise implementation plans, apply surgical search-and-replace code modifications, and summarize its work.

---

## 📁 Repository Structure

```
AI-Coding-Agent-Assignment/
├── ai-coding-agent/            # Python-based AI Agent source code
│   ├── agents/                 # Pipeline stages (Explorer, Planner, Modifier, Summarizer)
│   ├── prompts/                # Jinja2 prompt templates
│   ├── tools/                  # Repository search, file systems, and LLM utilities
│   ├── output/                 # Generated plans and change summaries
│   ├── .env.example            # Configuration template
│   └── main.py                 # Agent CLI Entrypoint
│
└── node-easy-notes-app/        # Sample target Node.js Express notes application
```

---

## ⚡ Key Features

- **Progressive Context Reduction:** Instead of dumping the entire repository into the LLM context, the **Explorer** iteratively reads only the relevant file slices needed for the task.
- **Surgical Search-and-Replace:** The **Modifier** performs line-by-line block matching to edit code instead of rewriting whole files, saving tokens and preserving code stability.
- **Multi-Provider LLM Integration:** Powered by an OpenAI-compatible client with a configuration system that supports **OpenAI**, **Groq**, and **Gemini**.
- **Self-Healing JSON Parsing:** Employs brace-balancing search algorithms to successfully parse flawed or double-closed JSON objects returned by smaller/older LLMs.
- **Safe Modifications:** Automatically creates backups (`.bak`) before applying changes and validates Python code syntax via `ast.parse` before committing.
- **Windows Console Safeguards:** Configured to handle UTF-8 print outputs to avoid standard terminal encoding errors during markdown summary formatting.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.11+
- Node.js (if testing the sample app)
- MongoDB (if running the sample app locally)

### 2. Installation
Navigate into the agent folder and install the dependencies:
```bash
cd ai-coding-agent
pip install -r requirements.txt
```

### 3. Configure the Environment
Create your `.env` configuration file from the template:
```bash
cp .env.example .env
```
Open `.env` and fill in your API credentials. 

#### Example Groq Setup (Free Tier):
```env
LLM_API_KEY=gsk_your_groq_api_key
LLM_BASE_URL=https://api.groq.com/openai/v1
MODEL_NAME=llama-3.3-70b-versatile
```

#### Example Gemini Setup (Google AI Studio Compatibility):
```env
LLM_API_KEY=AIzaSy_your_gemini_api_key
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/
MODEL_NAME=gemini-3.5-flash
```

---

## 💻 Running the Agent

Provide the absolute path of the target repository and your request. For example, to improve search and categorization in the notes app:

```bash
python main.py "../node-easy-notes-app" "Improve the application so users can better organise and search their notes."
```

### What Happens Behind the Scenes:
1. **Phase 1: Explore**
   The agent generates a directory tree, performs directory search operations, and slices relevant files (e.g., `app/models/note.model.js`, `app/controllers/note.controller.js`) to gather context.
2. **Phase 2: Plan**
   The agent formulates a step-by-step implementation plan and writes it to `output/plan.md`.
3. **Phase 3: Modify**
   The agent applies surgical search-and-replace edits to the target files, checking syntax along the way.
4. **Phase 4: Summarize**
   The agent writes a final markdown report of all changes applied, saving it to `output/summary.md` and printing a styled summary to the terminal.
