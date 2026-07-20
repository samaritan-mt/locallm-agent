import typer
import subprocess
import os

from tools import schemas
from audit.events import ToolExecutionEvent
from audit.logger import log_audit_event
from policy.config import SessionPolicyConfig

def execute_os_command(command: str):
    policy = SessionPolicyConfig()
    if not policy.can_execute_commands:
        return "POLICY_VIOLATION: Command execution is disabled by the current security policy."

    authorization = False
    while authorization == False:
        authorization = typer.confirm(f"[LocaLLM Security] Approve the execution of command: '{command}'")
        if authorization == True:
            try:
                result = subprocess.run(
    ["docker", "run", "--rm", "-v", f"{os.getcwd()}:/workspace", "-w", "/workspace", "python:3.11-alpine", "sh", "-c", command],
    capture_output=True,
    text=True,
    check=True
)
                event = ToolExecutionEvent(
                    tool_name=command,
                    arguments=command,
                    user_approved=authorization,
                    success=True
                )
                log_audit_event(event)
                output = result.stdout.strip()
                if not output:
                    output = "Command executed successfully but produced no output."
                return output
            except subprocess.CalledProcessError as e:
                event = ToolExecutionEvent(
                    tool_name=command,
                    arguments=command,
                    user_approved=authorization,
                    success=False
                )
                log_audit_event(event)
                err = e.stderr.strip() if e.stderr else str(e)
                return f"Error executing command: {err}"
        else:
            event = ToolExecutionEvent(
                tool_name=command,
                arguments=command,
                user_approved=authorization,
                success=False
            )
            log_audit_event(event)
            return "User denied the execution of the command."