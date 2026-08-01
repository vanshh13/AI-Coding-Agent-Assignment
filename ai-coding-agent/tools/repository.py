import re
from pathlib import Path
from typing import List, Dict, Any

def find_in_files(query: str, repo_path: Path, max_results: int = 50) -> List[Dict[str, Any]]:
    """Grep-like utility to scan files recursively for text matches.
    Ignores common dependencies/build files.
    """
    ignore_dirs = {
        ".git", "node_modules", "venv", ".venv", "env", "__pycache__", 
        "dist", "build", "output", ".idea", ".vscode"
    }
    
    results = []
    
    # Compile regex for case-insensitive search
    try:
        pattern = re.compile(query, re.IGNORECASE)
    except re.error:
        # If query is not a valid regex, treat it as a literal string
        pattern = re.compile(re.escape(query), re.IGNORECASE)

    def _search_dir(dir_path: Path):
        if len(results) >= max_results:
            return
            
        for path in dir_path.iterdir():
            if len(results) >= max_results:
                break
                
            if path.name.startswith(".") or path.name in ignore_dirs:
                continue
                
            if path.is_dir():
                _search_dir(path)
            elif path.is_file():
                # Avoid large lock files or binary files
                if path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip', '.tar', '.gz', '.db', '.sqlite', '.lock'}:
                    continue
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            if pattern.search(line):
                                results.append({
                                    "file": str(path.relative_to(repo_path)),
                                    "line": line_num,
                                    "content": line.strip()
                                })
                                if len(results) >= max_results:
                                    break
                except Exception:
                    # Ignore unreadable files
                    continue

    _search_dir(repo_path)
    return results
