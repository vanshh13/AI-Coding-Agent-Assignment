# AI Coding Agent

A lightweight, context-minimizing, and token-efficient AI agent designed to automatically explore codebases, formulate execution plans, perform surgical code modifications (using search-and-replace blocks), and summarize applied changes.

This application is built with a direct pipeline architecture, optimized for speed, explainability, and token saving—resembling lightweight coding assistants like **Cursor** or **Claude Code**.

---

## 🚀 Key Features

1. **Iterative Exploration & Context Filtering:** Rather than sending the entire codebase to the LLM, the agent starts with the repository tree and iteratively searches (grep) or reads specific file slices to dynamically build context.
2. **Surgical Search-and-Replace Block Edits:** Edits are performed by matching exact code blocks. This prevents file corruption, avoids context window bloat, and saves output tokens.
3. **Safety & Rollbacks:** Automatically creates `.bak` file backups before making edits and runs compilation/syntax checks. If a syntax error is introduced or a search block match fails, it automatically rolls back the changes.
4. **Detailed Artifacts:** Outputs both `plan.md` (pre-change planning) and `summary.md` (post-change report) to track progress.

---

## 🛠️ Tech Stack

* **Python 3.11+**
* **pathlib** (Native Object-Oriented Filesystem I/O)
* **Jinja2** (Prompt templating)
* **Rich** (Terminal output styling and markdown rendering)
* **python-dotenv** (Environment variable configurations)
* **OpenAI Client API** (Compatible with any OpenAI-compatible provider)

---

## 📂 Project Structure

```
ai-coding-agent/
│
├── main.py                # CLI entry point. Runs the pipeline stages sequentially.
├── config.py              # Configuration manager (Loads credentials and temperature settings).
├── requirements.txt       # Project dependency manifest.
├── .env.example           # Template environment configuration.
├── README.md              # Project documentation.
│
├── agents/                # Step-by-Step Pipeline Orchestrators
│   ├── explorer.py        # Dynamically discovers context (SEARCH, READ, DONE loops).
│   ├── planner.py         # Formulates step-by-step code change instructions.
│   ├── modifier.py        # Requests block modifications and applies them with backups.
│   └── summarizer.py      # Produces the final changelog report.
│
├── tools/                 # Native System & API Utilities
│   ├── llm.py             # Chat completions and Jinja2 prompt rendering.
│   ├── tree.py            # Generates depth-limited, ignore-aware directory trees.
│   ├── repository.py      # Grep search utility looking for code matches.
│   └── file.py            # Line-by-line reading, backups, and search-replace block updates.
│
├── prompts/               # Agent prompt templates
│   ├── explorer.txt       # Prompt for the iterative exploration steps.
│   ├── planner.txt        # Prompt for mapping requirements to plan.md.
│   ├── modifier.txt       # Prompt for surgical code replacement blocks.
│   └── summarizer.txt     # Prompt for formatting final summaries.
│
└── output/                # Actionable output artifacts
    ├── plan.md            # The generated implementation plan.
    ├── summary.md         # The final post-run modification changelog.
    └── logs.txt           # Console output transcript.
```

---

## ⚙️ Setup & Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   Copy the example environment file and open it:
   ```bash
   cp .env.example .env
   ```
   Add your API credentials and settings to the `.env` file:
   ```env
   LLM_API_KEY=your_api_key_here
   LLM_BASE_URL=https://api.openai.com/v1
   MODEL_NAME=gpt-4o-mini
   TEMPERATURE=0.0
   MAX_ITERATIONS=5
   ```

### 💡 Support for Groq and Gemini (OpenAI Compatibility Mode)

The agent uses a generic API wrapper. You can connect it to any provider by pointing the URL and passing the key:

* **For Groq:**
  ```env
  LLM_API_KEY=your_api_key_here
  LLM_BASE_URL=https://api.groq.com/openai/v1
  MODEL_NAME=llama-3.3-70b-versatile
  ```

* **For Gemini:**
  ```env
  LLM_API_KEY=your_api_key_here
  LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
  MODEL_NAME=gemini-2.5-flash
  ```


---

## 💻 Usage

Execute the agent by providing the absolute/relative path of the target codebase and the modification request:

```bash
python main.py <target_repository_path> "<request>"
```

### Example

To run the agent against a sample Express notes app to add search functionality:

```bash
python main.py "../node-easy-notes-app" "Improve the application so users can better organise and search their notes."
```

During execution, the console output will show:
1. **Phase 1 (Explore):** Logged outputs of the agent discovering the codebase and pulling slices of `server.js` and controller files.
2. **Phase 2 (Plan):** The compiled plan written to `output/plan.md`.
3. **Phase 3 (Modify):** Surgical search-and-replace block changes applied to routers, controllers, and schemas.
4. **Phase 4 (Summarize):** A styled Rich console layout displaying the final changelog written to `output/summary.md`.
