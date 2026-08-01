from pathlib import Path
from typing import Dict, List, Any
from tools.llm import LLMHelper
from tools.tree import generate_tree
from tools.repository import find_in_files
from tools.file import read_lines

class Explorer:
    @staticmethod
    def explore(repo_path: Path, request: str, llm: LLMHelper) -> Dict[str, str]:
        """Runs the iterative repository exploration loop.
        Decides dynamically which files to read or search, saving context tokens.
        """
        snippets: List[Dict[str, Any]] = []
        # Keep track of read line ranges to avoid repeating the exact same read
        read_history = set()

        for iteration in range(1, llm.config.MAX_ITERATIONS + 1):
            tree_str = generate_tree(repo_path)
            
            # Format collected snippets for the LLM context
            formatted_snippets = []
            for snip in snippets:
                formatted_snippets.append({
                    "file_path": snip["file_path"],
                    "start_line": snip["start_line"],
                    "end_line": snip["end_line"],
                    "content": snip["content"]
                })

            prompt = llm.render_prompt(
                "explorer.txt", 
                {
                    "request": request, 
                    "tree": tree_str, 
                    "snippets": formatted_snippets
                }
            )

            # Request JSON command response
            response = llm.call_json(prompt, system_message="You are an agent exploring a repository. Output valid JSON only.")
            
            action = response.get("action")
            thought = response.get("thought", "")
            param = response.get("param")

            print(f"[Explorer Step {iteration}] Thought: {thought}")

            if action == "DONE" or not action:
                print("[Explorer] Finished exploration.")
                break

            elif action == "SEARCH":
                query = str(param)
                print(f"[Explorer] Action: Searching repository for query: '{query}'")
                search_results = find_in_files(query, repo_path)
                
                # Format search results into a snippet
                if search_results:
                    result_summary = "\n".join([
                        f"Found in {res['file']} (Line {res['line']}): {res['content']}" 
                        for res in search_results
                    ])
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
                    
                    # Prevent circular reading loops of exact same file slices
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
        # Ignore virtual "Search Results" snippets in final file context map
        final_context: Dict[str, str] = {}
        for snip in snippets:
            path_str = snip["file_path"]
            if not path_str.startswith("Search Results:"):
                # If we read multiple segments of the same file, merge them
                if path_str in final_context:
                    final_context[path_str] += f"\n...\n{snip['content']}"
                else:
                    final_context[path_str] = snip["content"]

        return final_context
