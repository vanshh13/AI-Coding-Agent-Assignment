from pathlib import Path
from typing import List

def generate_tree(repo_path: Path, max_depth: int = 4, current_depth: int = 1) -> str:
    """Generates a text-based ASCII tree representing directory structure.
    Filters out common build directories, dependencies, and venvs.
    """
    ignore_dirs = {
        ".git", "node_modules", "venv", ".venv", "env", "__pycache__", 
        "dist", "build", "output", ".idea", ".vscode"
    }
    
    if not repo_path.exists():
        return f"Path {repo_path} does not exist."

    lines = []
    
    def _walk(directory: Path, prefix: str = "", depth: int = 1):
        if depth > max_depth:
            lines.append(f"{prefix}... (depth limit reached)")
            return
            
        try:
            # Sort directories first, then files
            children = sorted(
                list(directory.iterdir()), 
                key=lambda p: (not p.is_dir(), p.name.lower())
            )
        except PermissionError:
            lines.append(f"{prefix}[Permission Denied]")
            return

        # Filter children
        filtered_children = [
            c for c in children if c.name not in ignore_dirs and not c.name.startswith(".")
        ]

        count = len(filtered_children)
        for i, child in enumerate(filtered_children):
            is_last = (i == count - 1)
            connector = "└── " if is_last else "├── "
            
            lines.append(f"{prefix}{connector}{child.name}")
            
            if child.is_dir():
                extension = "    " if is_last else "│   "
                _walk(child, prefix + extension, depth + 1)

    lines.append(repo_path.name)
    _walk(repo_path)
    return "\n".join(lines)
