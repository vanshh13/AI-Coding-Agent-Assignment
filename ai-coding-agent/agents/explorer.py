import re
import json
from pathlib import Path
from typing import Dict, List, Any
from tools.llm import LLMHelper
from tools.tree import generate_tree
from tools.repository import find_in_files
from tools.file import read_lines

def detect_project_metadata(repo_path: Path) -> Dict[str, Any]:
    """Scans the repository to identify framework, key dependencies, and entry points."""
    metadata = {
        "project_type": "Unknown",
        "detected_frameworks": [],
        "entry_points": [],
        "primary_dependencies": []
    }
    
    # 1. Check Node.js
    package_json_path = repo_path / "package.json"
    if package_json_path.exists():
        metadata["project_type"] = "Node.js (npm package detected)"
        try:
            with open(package_json_path, 'r', encoding='utf-8', errors='ignore') as f:
                data = json.load(f)
            
            if "main" in data:
                metadata["entry_points"].append(data["main"])
            if "scripts" in data:
                for script_val in data["scripts"].values():
                    js_files = re.findall(r'(\w+\.js)', script_val)
                    metadata["entry_points"].extend(js_files)
            
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            metadata["primary_dependencies"] = list(deps.keys())[:15]
            
            for fw in ["express", "nestjs", "react", "next", "vue", "angular", "fastify", "koa"]:
                if fw in deps or any(fw in d.lower() for d in deps):
                    metadata["detected_frameworks"].append(fw.capitalize())
        except Exception:
            pass

    # 2. Check Python
    requirements_path = repo_path / "requirements.txt"
    pyproject_path = repo_path / "pyproject.toml"
    if requirements_path.exists() or pyproject_path.exists():
        metadata["project_type"] = "Python"
        dependencies = []
        if requirements_path.exists():
            try:
                with open(requirements_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            dep_name = re.split(r'[=<>]', line)[0].strip()
                            dependencies.append(dep_name)
                metadata["primary_dependencies"] = dependencies[:15]
            except Exception:
                pass
        
        for fw in ["django", "flask", "fastapi", "tornado", "pyramid"]:
            if any(fw in dep.lower() for dep in dependencies):
                metadata["detected_frameworks"].append(fw.capitalize())

    # 3. Scan common entry points in root
    for common_name in ["server.js", "app.js", "index.js", "main.py", "app.py", "wsgi.py", "index.php"]:
        if (repo_path / common_name).exists() and common_name not in metadata["entry_points"]:
            metadata["entry_points"].append(common_name)
            
    metadata["entry_points"] = list(set(metadata["entry_points"]))
    return metadata

def consolidate_snippets(snippets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Groups gathered snippets by file name and merges overlapping/adjacent ranges."""
    file_snippets: Dict[str, List[tuple]] = {}
    search_snippets = []
    
    for snip in snippets:
        path = snip["file_path"]
        if path.startswith("Search Results:"):
            search_snippets.append(snip)
        else:
            content_lines = snip["content"].splitlines()
            file_snippets.setdefault(path, []).append((snip["start_line"], snip["end_line"], content_lines))
            
    consolidated = []
    consolidated.extend(search_snippets)
    
    for path, segments in file_snippets.items():
        segments.sort(key=lambda x: x[0])
        
        merged_segments = []
        for start, end, lines in segments:
            if not merged_segments:
                merged_segments.append((start, end, lines))
            else:
                last_start, last_end, last_lines = merged_segments[-1]
                if last_end >= start - 1:
                    overlap = last_end - start + 1
                    unique_new_lines = lines[overlap:] if overlap > 0 else lines
                    new_end = max(last_end, end)
                    new_lines = last_lines + unique_new_lines
                    merged_segments[-1] = (last_start, new_end, new_lines)
                else:
                    merged_segments.append((start, end, lines))
                    
        for start, end, lines in merged_segments:
            consolidated.append({
                "file_path": path,
                "start_line": start,
                "end_line": end,
                "content": "\n".join(lines)
            })
            
    return consolidated

class Explorer:
    @staticmethod
    def explore(repo_path: Path, request: str, llm: LLMHelper) -> Dict[str, str]:
        """Runs the iterative repository exploration loop with metadata discovery and snippet caching."""
        snippets: List[Dict[str, Any]] = []
        read_history = set()
        
        # 1. Performance: Scan directory tree and metadata exactly once
        tree_str = generate_tree(repo_path)
        metadata = detect_project_metadata(repo_path)
        metadata_str = json.dumps(metadata, indent=2)

        for iteration in range(1, llm.config.MAX_ITERATIONS + 1):
            # 2. Token Reduction: Group and merge overlapping slices of code snippets
            consolidated_snippets = consolidate_snippets(snippets)
            
            prompt = llm.render_prompt(
                "explorer.txt", 
                {
                    "request": request,
                    "metadata": metadata_str,
                    "tree": tree_str, 
                    "snippets": consolidated_snippets
                }
            )

            response = llm.call_json(prompt, system_message="You are an agent exploring a repository. Output valid JSON only.")
            
            action = response.get("action")
            thought = response.get("thought", "")
            param = response.get("param")

            print(f"[Explorer Step {iteration}] Thought: {thought}")

            if action == "DONE" or not action:
                print("[Explorer] Finished exploration.")
                break

            elif action == "SEARCH":
                query = str(param) if not isinstance(param, dict) else json.dumps(param)
                print(f"[Explorer] Action: Searching repository for query: '{query}'")
                search_results = find_in_files(query, repo_path)
                
                if search_results:
                    grouped = {}
                    for res in search_results:
                        grouped.setdefault(res["file"], []).append(
                            f"  - Line {res['line']}: {res['content']}\n"
                            f"    Context:\n"
                            f"    {res['context'].replace('\n', '\n    ')}"
                        )
                    
                    summary_parts = []
                    for fpath, matches in grouped.items():
                        summary_parts.append(f"File: {fpath}\n" + "\n".join(matches))
                    result_summary = "\n\n".join(summary_parts)
                else:
                    result_summary = "No matches found."

                snippets.append({
                    "file_path": f"Search Results: '{query}'",
                    "start_line": 1,
                    "end_line": len(search_results) or 1,
                    "content": result_summary
                })

            elif action == "READ":
                if isinstance(param, dict):
                    file_name = param.get("file", "")
                    start = int(param.get("start", 1))
                    end = int(param.get("end", 100))
                    
                    history_key = (file_name, start, end)
                    if history_key in read_history:
                        print(f"[Explorer] Warning: Already read {file_name}:{start}-{end}. Skipping.")
                        continue
                    
                    read_history.add(history_key)
                    print(f"[Explorer] Action: Reading file slice {file_name} (Lines {start}-{end})")
                    
                    full_path = repo_path / file_name
                    content = read_lines(full_path, start, end)
                    
                    snippets.append({
                        "file_path": file_name,
                        "start_line": start,
                        "end_line": end,
                        "content": content
                    })
                else:
                    print("[Explorer] Error: Invalid READ parameters.")

        # Consolidate snippets by file name for subsequent stages
        final_context: Dict[str, str] = {}
        file_only_snippets = [s for s in snippets if not s["file_path"].startswith("Search Results:")]
        merged_file_snippets = consolidate_snippets(file_only_snippets)
        for snip in merged_file_snippets:
            final_context[snip["file_path"]] = snip["content"]

        return final_context
