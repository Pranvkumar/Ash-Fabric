"""
Script Manager — Discovers and manages remediation scripts.
Used by agents to list, read, and validate available automation.
"""

from pathlib import Path
import structlog

logger = structlog.get_logger()


class ScriptManager:
    SUPPORTED_EXTENSIONS = {".sh", ".py", ".tf", ".hcl", ".yml", ".yaml"}

    def __init__(self, scripts_dir: str):
        self.scripts_dir = Path(scripts_dir)
        self.scripts_dir.mkdir(parents=True, exist_ok=True)

    def list_scripts(self) -> list[str]:
        """List all available remediation scripts."""
        scripts = []
        for ext in self.SUPPORTED_EXTENSIONS:
            for path in self.scripts_dir.rglob(f"*{ext}"):
                scripts.append(path.name)
        return sorted(scripts)

    def get_script_path(self, script_name: str) -> str | None:
        """Get the full path of a script by name."""
        for ext in self.SUPPORTED_EXTENSIONS:
            for path in self.scripts_dir.rglob(f"*{ext}"):
                if path.name == script_name:
                    return str(path)
        return None

    def get_script_content(self, script_name: str) -> str | None:
        """Read the content of a script (for LLM analysis)."""
        path = self.get_script_path(script_name)
        if path:
            return Path(path).read_text()
        return None

    def count_scripts(self) -> int:
        return len(self.list_scripts())

    def validate_script(self, script_name: str) -> dict:
        """Basic validation of a script file."""
        path = self.get_script_path(script_name)
        if not path:
            return {"valid": False, "error": "Script not found"}

        p = Path(path)
        return {
            "valid": True,
            "name": script_name,
            "size": p.stat().st_size,
            "extension": p.suffix,
            "readable": p.is_file(),
        }
