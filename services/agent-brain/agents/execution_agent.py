"""
Execution Agent — Runs remediation scripts with dynamic variable injection.
Manages Terraform apply, Ansible playbooks, and shell scripts.
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import structlog

from tools.script_manager import ScriptManager
from config.settings import Settings

logger = structlog.get_logger()


class ExecutionAgent:
    def __init__(self, script_manager: ScriptManager, settings: Settings):
        self.scripts = script_manager
        self.settings = settings
        self.execution_log: list[dict] = []

    async def run_script(self, script_name: str, service: str, variables: dict) -> dict:
        """
        Execute a remediation script with variable injection.
        Supports: .sh (bash), .py (python), .tf (terraform), .yml (ansible).
        """
        script_path = self.scripts.get_script_path(script_name)
        if not script_path:
            raise FileNotFoundError(f"Script not found: {script_name}")

        logger.info(
            "executing_script",
            script=script_name,
            service=service,
            variables=variables,
        )

        # Build environment variables for the script
        env = os.environ.copy()
        env["ASH_SERVICE"] = service
        env["ASH_TIMESTAMP"] = datetime.now(timezone.utc).isoformat()
        for key, value in variables.items():
            env[f"ASH_{key.upper()}"] = str(value)

        # Determine execution method
        ext = Path(script_name).suffix.lower()
        result = {}

        if ext == ".sh":
            result = await self._run_shell(script_path, env)
        elif ext == ".py":
            result = await self._run_python(script_path, env)
        elif ext in (".tf", ".hcl"):
            result = await self._run_terraform(script_path, variables)
        elif ext in (".yml", ".yaml"):
            result = await self._run_ansible(script_path, variables, service)
        else:
            raise ValueError(f"Unsupported script type: {ext}")

        # Log execution
        log_entry = {
            "script": script_name,
            "service": service,
            "exit_code": result.get("exit_code", -1),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": result.get("exit_code", -1) == 0,
        }
        self.execution_log.append(log_entry)
        self._save_execution_log(log_entry)

        return result

    async def _run_shell(self, script_path: str, env: dict) -> dict:
        """Execute a bash script."""
        proc = await asyncio.create_subprocess_exec(
            "bash", script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        return {
            "exit_code": proc.returncode,
            "stdout": stdout.decode()[-2000:],  # Last 2KB
            "stderr": stderr.decode()[-2000:],
        }

    async def _run_python(self, script_path: str, env: dict) -> dict:
        """Execute a Python script."""
        proc = await asyncio.create_subprocess_exec(
            "python3", script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        return {
            "exit_code": proc.returncode,
            "stdout": stdout.decode()[-2000:],
            "stderr": stderr.decode()[-2000:],
        }

    async def _run_terraform(self, script_path: str, variables: dict) -> dict:
        """Execute terraform plan/apply (mock-safe)."""
        tf_dir = str(Path(script_path).parent)
        var_args = []
        for k, v in variables.items():
            var_args.extend(["-var", f"{k}={v}"])

        # Plan first (safe)
        proc = await asyncio.create_subprocess_exec(
            "terraform", "plan", "-no-color", *var_args,
            cwd=tf_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

        return {
            "exit_code": proc.returncode,
            "stdout": stdout.decode()[-4000:],
            "stderr": stderr.decode()[-2000:],
            "mode": "plan_only",  # Apply requires approval gate
        }

    async def _run_ansible(self, script_path: str, variables: dict, service: str) -> dict:
        """Execute an Ansible playbook."""
        extra_vars = json.dumps({**variables, "target_service": service})
        proc = await asyncio.create_subprocess_exec(
            "ansible-playbook", script_path,
            "--extra-vars", extra_vars,
            "--check",  # Dry-run mode by default (safety)
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

        return {
            "exit_code": proc.returncode,
            "stdout": stdout.decode()[-4000:],
            "stderr": stderr.decode()[-2000:],
            "mode": "check_only",
        }

    def _save_execution_log(self, entry: dict):
        """Persist execution log to disk."""
        log_dir = Path(self.settings.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "execution_log.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
