"""Application settings loaded from environment variables."""

import os
from dataclasses import dataclass, field
from pathlib import Path

# Resolve project root: agent-brain is at <project>/services/agent-brain
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DEFAULT_SCRIPTS_DIR = str(_PROJECT_ROOT / "scripts")


@dataclass
class Settings:
    nats_url: str = field(default_factory=lambda: os.getenv("NATS_URL", "nats://localhost:4222"))
    vm_endpoint: str = field(default_factory=lambda: os.getenv("VM_ENDPOINT", "http://localhost:8428"))
    scripts_dir: str = field(default_factory=lambda: os.getenv("SCRIPTS_DIR", _DEFAULT_SCRIPTS_DIR))
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "llama3"))
    log_dir: str = field(default_factory=lambda: os.getenv("LOG_DIR", "./logs"))
    approval_required: bool = field(
        default_factory=lambda: os.getenv("APPROVAL_REQUIRED", "false").lower() == "true"
    )
