from pathlib import Path
from typing import List, Dict, Any
from tools.llm import LLMHelper
from tools.file import write_file

class Summarizer:
    @staticmethod
    def summarize(edits: List[Dict[str, Any]], llm: LLMHelper) -> str:
        """Generates a markdown change summary and saves it to output/summary.md."""
        prompt = llm.render_prompt(
            "summarizer.txt",
            {
                "edits": edits
            }
        )

        # Retrieve plain text markdown summary from LLM
        summary_markdown = llm.call_text(
            prompt, 
            system_message="You are a technical documentation assistant. Generate clear markdown logs."
        )

        output_summary_path = Path(__file__).parent.parent / "output" / "summary.md"
        print(f"[Summarizer] Writing execution summary to {output_summary_path.relative_to(Path(__file__).parent.parent)}")
        write_file(output_summary_path, summary_markdown)

        return summary_markdown
