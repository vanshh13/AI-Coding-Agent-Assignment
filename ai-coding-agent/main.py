import sys
import argparse
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.markdown import Markdown
from config import Config
from tools.llm import LLMHelper
from agents.explorer import Explorer
from agents.planner import Planner
from agents.modifier import Modifier
from agents.summarizer import Summarizer

# Force UTF-8 stdout/stderr on Windows to avoid UnicodeEncodeErrors
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass


console = Console()

def setup_logger(log_path: Path):
    """Simple logger helper that appends records to log_path."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def log(message: str, style: str = "white"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        plain_text = f"[{timestamp}] {message}"
        # Append to log file
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(plain_text + "\n")
        # Print styled version to console
        console.print(f"[bold cyan][{timestamp}][/bold cyan] {message}", style=style)
        
    return log

def main():
    parser = argparse.ArgumentParser(description="AI Coding Agent - Automatically edit and improve a codebase.")
    parser.add_argument("repo_path", type=str, help="Path to target repository to modify")
    parser.add_argument("request", type=str, help="User request description of changes required")
    
    args = parser.parse_args()
    
    repo_path = Path(args.repo_path).resolve()
    request = args.request
    
    log_path = Path(__file__).parent / "output" / "logs.txt"
    # Clear previous logs for this run
    if log_path.exists():
        log_path.unlink()
        
    log = setup_logger(log_path)
    
    log("=========================================")
    log("Starting AI Coding Agent Session")
    log(f"Repository Path: {repo_path}")
    log(f"User Request: {request}")
    log("=========================================")
    
    # 1. Validation & Setup
    if not repo_path.exists() or not repo_path.is_dir():
        log(f"Error: Provided repository path does not exist or is not a directory: {repo_path}", style="bold red")
        sys.exit(1)
        
    config = Config()
    if not config.LLM_API_KEY:
        log("Warning: LLM_API_KEY environment variable is empty. Ensure local API base URL doesn't require key authentication.", style="bold yellow")
        
    try:
        llm = LLMHelper(config)
    except Exception as e:
        log(f"Failed to initialize LLM client: {str(e)}", style="bold red")
        sys.exit(1)
        
    # 2. Phase 1: Explore
    log("Phase 1: Exploring repository and gathering relevant files...")
    try:
        explorer_context = Explorer.explore(repo_path, request, llm)
        log(f"Exploration complete. Found {len(explorer_context)} relevant files.")
        for f in explorer_context.keys():
            log(f"  - Relevant context loaded: {f}")
    except Exception as e:
        log(f"Exploration phase failed: {str(e)}", style="bold red")
        sys.exit(1)
        
    if not explorer_context:
        log("No relevant files identified by the explorer. Proceeding with planning using tree structure only.", style="yellow")
        
    # 3. Phase 2: Plan
    log("Phase 2: Formulating change implementation plan...")
    try:
        plan_details = Planner.plan(request, explorer_context, llm)
        log("Plan formulated successfully.")
    except Exception as e:
        log(f"Planning phase failed: {str(e)}", style="bold red")
        sys.exit(1)
        
    # 4. Phase 3: Modify
    log("Phase 3: Applying targeted search-and-replace modifications...")
    try:
        edit_results = Modifier.modify(repo_path, plan_details, request, llm)
        success_count = sum(1 for edit in edit_results if edit["success"])
        log(f"Modification phase complete. Successfully updated {success_count}/{len(edit_results)} target files.")
        for edit in edit_results:
            status = "[bold green]Success[/bold green]" if edit["success"] else f"[bold red]Failed: {edit['error']}[/bold red]"
            log(f"  - File {edit['file_path']}: {status}")
    except Exception as e:
        log(f"Modification phase failed: {str(e)}", style="bold red")
        sys.exit(1)
        
    # 5. Phase 4: Summarize
    log("Phase 4: Generating final change summary...")
    try:
        summary_markdown = Summarizer.summarize(edit_results, llm)
        log("Summary created successfully. Session complete.")
        log("=========================================")
        log("Final Change Summary:")
        console.print(Markdown(summary_markdown))
    except Exception as e:
        log(f"Summarization phase failed: {str(e)}", style="bold red")
        sys.exit(1)

if __name__ == "__main__":
    main()
