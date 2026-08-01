import re
import json
from pathlib import Path
from typing import List, Dict, Any
from tools.file import read_file_cached

def find_in_files(query: str, repo_path: Path, max_results: int = 50) -> List[Dict[str, Any]]:
    """Grep-like utility to scan files recursively for text matches.
    Supports basic string queries, JSON-based advanced regex queries,
    and returns matches with surrounding context lines.
    """
    query_str = query
    file_extensions = None
    exclude_dirs = {
        ".git", "node_modules", "venv", ".venv", "env", "__pycache__", 
        "dist", "build", "output", ".idea", ".vscode"
    }
    include_dirs = None
    case_sensitive = False
    context_lines = 2

    # Try parsing query as JSON for advanced search parameters
    stripped_query = query.strip()
    if stripped_query.startswith("{") and stripped_query.endswith("}"):
        try:
            params = json.loads(stripped_query)
            query_str = params.get("query", query)
            case_sensitive = params.get("case_sensitive", False)
            context_lines = params.get("context_lines", 2)
            
            if "file_extensions" in params:
                file_extensions = [
                    ext.lower() if ext.startswith('.') else f".{ext.lower()}" 
                    for ext in params["file_extensions"]
                ]
                
            if "exclude_dirs" in params:
                exclude_dirs.update(params["exclude_dirs"])
                
            if "include_dirs" in params:
                include_dirs = [Path(d) for d in params["include_dirs"]]
        except Exception:
            pass

    results = []
    
    # Compile regex pattern
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        pattern = re.compile(query_str, flags)
    except re.error:
        # Fallback to literal search if regex is invalid
        pattern = re.compile(re.escape(query_str), flags)

    def _search_dir(dir_path: Path):
        if len(results) >= max_results:
            return
            
        for path in dir_path.iterdir():
            if len(results) >= max_results:
                break
                
            # Filter directories
            if path.is_dir():
                if path.name.startswith(".") or path.name in exclude_dirs:
                    continue
                # If include_dirs is set, only traverse if this dir matches or contains/is contained in include_dirs
                if include_dirs:
                    is_relevant = False
                    for inc in include_dirs:
                        inc_abs = (repo_path / inc).resolve()
                        path_abs = path.resolve()
                        if path_abs == inc_abs or inc_abs in path_abs.parents or path_abs in inc_abs.parents:
                            is_relevant = True
                            break
                    if not is_relevant:
                        continue
                _search_dir(path)
                
            # Filter files
            elif path.is_file():
                if path.name.startswith("."):
                    continue
                    
                # Extension filtering
                if file_extensions and path.suffix.lower() not in file_extensions:
                    continue
                    
                # Exclude binary / large files
                if path.suffix.lower() in {
                    '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip', '.tar', 
                    '.gz', '.db', '.sqlite', '.lock', '.ico', '.woff', '.woff2', '.ttf'
                }:
                    continue
                
                # Check include_dirs
                if include_dirs:
                    is_included = False
                    for inc in include_dirs:
                        inc_abs = (repo_path / inc).resolve()
                        path_abs = path.resolve()
                        if path_abs == inc_abs or inc_abs in path_abs.parents:
                            is_included = True
                            break
                    if not is_included:
                        continue

                try:
                    # Use cached file reader to avoid redundant disk I/O
                    file_content = read_file_cached(path)
                    if not file_content:
                        continue
                        
                    if pattern.search(file_content):
                        all_lines = file_content.splitlines()
                        for match in pattern.finditer(file_content):
                            if len(results) >= max_results:
                                break
                                
                            start_offset = match.start()
                            # Calculate 1-indexed line number
                            line_num = file_content.count('\n', 0, start_offset) + 1
                            
                            # Grab context lines
                            start_idx = max(0, line_num - 1 - context_lines)
                            end_idx = min(len(all_lines), line_num + context_lines)
                            
                            context_lines_list = []
                            for idx in range(start_idx, end_idx):
                                prefix = "-> " if idx == line_num - 1 else "   "
                                context_lines_list.append(f"{idx + 1}:{prefix}{all_lines[idx]}")
                            
                            results.append({
                                "file": str(path.relative_to(repo_path)),
                                "line": line_num,
                                "content": all_lines[line_num - 1].strip(),
                                "context": "\n".join(context_lines_list)
                            })
                except Exception:
                    continue

    _search_dir(repo_path)
    return results
