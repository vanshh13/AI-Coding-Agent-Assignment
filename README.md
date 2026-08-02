# AI Coding Agent Assignment

A lightweight AI coding assistant built in Python that explores a repository, generates an implementation plan, applies targeted code changes, and summarizes the results.

---

## Repository Structure

```text
AI-Coding-Agent-Assignment/
├── ai-coding-agent/            # Python agent
│   ├── agents/                 # Explorer, Planner, Modifier, Summarizer
│   ├── prompts/                # Jinja2 prompt templates
│   ├── tools/                  # Repository, filesystem, and LLM utilities
│   ├── output/                 # Generated plans and summaries
│   ├── .env.example            # Environment configuration template
│   └── main.py                 # Entry point
│
└── node-easy-notes-app/        # Sample target repository
```

---

## Features

- Explores the repository incrementally to gather only the relevant context.
- Generates an implementation plan before making changes.
- Applies targeted search-and-replace code modifications.
- Supports OpenAI-compatible providers such as OpenAI, Groq, and Gemini.
- Creates backups before modifying files and validates Python syntax after edits.
- Produces a summary of the applied changes.

---

## Prerequisites

- Python 3.11+
- Node.js (optional, for testing the sample application)
- MongoDB (optional, if running the sample application locally)

---

## Installation

Navigate to the agent directory and install the dependencies:

```bash
cd ai-coding-agent
pip install -r requirements.txt
```

---

## Configuration

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Configure your preferred LLM provider.

### Example (Groq)

```env
LLM_API_KEY=your_groq_api_key
LLM_BASE_URL=https://api.groq.com/openai/v1
MODEL_NAME=llama-3.3-70b-versatile
```

### Example (Gemini)

```env
LLM_API_KEY=your_gemini_api_key
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/
MODEL_NAME=gemini-3.5-flash
```

---

## Usage

Run the agent by providing the target repository and the requested task.

```bash
python main.py "../node-easy-notes-app" "Improve the application so users can better organise and search their notes."
```

---

## Workflow

1. Explore the repository to identify relevant files.
2. Generate an implementation plan.
3. Apply targeted code modifications.
4. Generate a summary of the changes.

Generated outputs are written to the `output/` directory:

- `plan.md` – implementation plan
- `summary.md` – summary of applied changes

---

## Notes

- The modifier creates `.bak` files before editing source files.
- Python files are validated for syntax before changes are finalized.
- The agent is designed to minimize unnecessary context sent to the LLM by exploring repositories incrementally.
