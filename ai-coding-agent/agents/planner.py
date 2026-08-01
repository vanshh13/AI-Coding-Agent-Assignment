from pathlib import Path
from typing import Dict, Any, List
from tools.llm import LLMHelper
from tools.file import write_file

class Planner:
    @staticmethod
    def plan(request: str, explorer_context: Dict[str, str], llm: LLMHelper) -> Dict[str, Any]:
        """Formulates an implementation plan and returns target files to edit.
        Saves the markdown plan to output/plan.md.
        """
        # Convert dictionary to snippet format for template rendering
        snippets = []
        for path_str, content in explorer_context.items():
            snippets.append({
                "file_path": path_str,
                "start_line": 1,
                "end_line": len(content.split('\n')),
                "content": content
            })

        prompt = llm.render_prompt(
            "planner.txt",
            {
                "request": request,
                "snippets": snippets
            }
        )

        response = llm.call_json(prompt, system_message="You are a system planner. Output valid JSON only.")
        
        plan_markdown = response.get("plan_markdown", "# Implementation Plan\n\nNo plan generated.")
        files_to_edit = response.get("files_to_edit", [])

        # Ensure files_to_edit is a list of strings
        if not isinstance(files_to_edit, list):
            files_to_edit = []

        # Save to output/plan.md
        output_plan_path = Path(__file__).parent.parent / "output" / "plan.md"
        print(f"[Planner] Writing implementation plan to {output_plan_path.relative_to(Path(__file__).parent.parent)}")
        write_file(output_plan_path, plan_markdown)

        return {
            "plan_markdown": plan_markdown,
            "files_to_edit": files_to_edit
        }
