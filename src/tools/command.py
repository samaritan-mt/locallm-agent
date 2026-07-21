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

    authorization = typer.confirm(f"[LocaLLM Security] Approve the execution of command: '{command}'")
    
    if authorization:
        try:
            result = subprocess.run(
                ["docker", "exec", "locallm-sandbox", "sh", "-c", command],
                capture_output=True,
                text=True,
                check=True
            )
            event = ToolExecutionEvent(tool_name="execute_os_command", arguments=command, user_approved=True, success=True)
            log_audit_event(event)
            output = result.stdout.strip()
            if not output:
                output = "Command executed successfully but produced no output."
            return output
        except subprocess.CalledProcessError as e:
            event = ToolExecutionEvent(tool_name="execute_os_command", arguments=command, user_approved=True, success=False)
            log_audit_event(event)
            err = e.stderr.strip() if e.stderr else str(e)
            return f"Error executing command: {err}"
    else:
        return "User denied the execution of the command."


def write_file(filepath: str, content: str):
    authorization = False
    authorization = typer.confirm(f"[LocaLLM Security] Approve writing to file: '{filepath}'")
    if authorization == True:
        try:
            abs_path = os.path.abspath(filepath)
            if not abs_path.startswith(os.getcwd()):
                return "Security Violation: Cannot write files outside the workspace." 
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            event = ToolExecutionEvent(
                tool_name="write_file",
                arguments=f"filepath={filepath}",
                user_approved=True,
                success=True
            )
            log_audit_event(event)
            return f"Successfully wrote to {filepath}"
        except Exception as e:
            return f"Error writing to file: {str(e)}"
    else:
        return "User denied writing to the file."


def read_file(filepath: str):
    try:
        abs_path = os.path.abspath(filepath)
        if not abs_path.startswith(os.getcwd()):
            return "Security Violation: Cannot read files outside the workspace."
        if not os.path.exists(filepath):
            return f"Error: File '{filepath}' does not exist."
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"