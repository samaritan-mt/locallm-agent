import typer
from policy.config import AllowedModels
from llm import *
from audit.events import AskAuditEvent
from audit.logger import log_audit_event

app = typer.Typer( no_args_is_help=True,
    help="LocalSec Agent — A local-first macOS AI assistant for security engineers.",
    epilog="Designed for DevSecOps workflows. Enforces strict local boundaries.")

@app.command(name="ask")
def ask_command(
    prompt: str = typer.Argument(..., help="The prompt or question to send to the local model."),
    model: AllowedModels = typer.Option(AllowedModels.QWEN, help="The Ollama model to use for inference."),
    temperature: float = typer.Option(0.2, min=0.0, max=1.0, help="Controls model creativity (0.0 to 1.0)."),
    max_input_chars: int = typer.Option(8000, help="Maximum allowed prompt size to prevent overflow."),
    allow_remote_endpoint: bool = typer.Option(False, help="DANGER: Permit non-local Ollama endpoints."),
    debug_log: bool = typer.Option(False, "--debug-log", help="Opt-in to log full prompts (DANGER)")
):
    """
    Securely ask a question to your local AI model.
    
    This command sends your prompt to a local Ollama instance. It enforces strict
    system boundaries to ensure the model cannot act, read files, or access the network.
    
    Examples:
    
    $ localai ask "Explain least privilege in IAM"
    
    $ localai ask "What is the difference between SAST and DAST?" --model mistral:7b
    """
    if debug_log:
        typer.secho("WARNING: Debug logging may store prompt and response content locally.", fg=typer.colors.RED)

    
    try:
        answer = query_local_llm(model,temperature, max_input_chars, allow_remote_endpoint, prompt)
        event = AskAuditEvent(
            model=model.value if hasattr(model, 'value') else model,
            input_chars=len(prompt),
            success=True,
            endpoint_type="remote" if allow_remote_endpoint else "local"
        )
        log_audit_event(event)
        print(f"A: {answer}")
    except Exception as e:
        event = AskAuditEvent(
            model=model.value if hasattr(model, 'value') else model,
            input_chars=len(prompt),
            success=False,
            endpoint_type="remote" if allow_remote_endpoint else "local"
        )
        log_audit_event(event)
        raise
@app.command("help",)
def help_command():
    print("""
    Securely ask a question to your local AI model.
    
    This command sends your prompt to a local Ollama instance. It enforces strict
    system boundaries to ensure the model cannot act, read files, or access the network.
    
    Examples:
    
    $ localai ask "Explain least privilege in IAM"
    
    $ localai ask "What is the difference between SAST and DAST?" --model mistral:7b
    """)
    
if __name__ == "__main__":
    app()
