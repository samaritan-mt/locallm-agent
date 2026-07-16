import typer
from policy.config import AllowedModels
from llm import *
from audit.events import AskAuditEvent,SessionAuditEvent
from audit.logger import log_audit_event
from session import SecureChatSession

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
@app.command("help")
def help_command():
    print("""
    Securely ask a question to your local AI model.
    
    This command sends your prompt to a local Ollama instance. It enforces strict
    system boundaries to ensure the model cannot act, read files, or access the network.
    
    Examples:
    
    $ localai ask "Explain least privilege in IAM"
    
    $ localai ask "What is the difference between SAST and DAST?" --model mistral:7b
    """)

@app.command("agent")
def agent_command():
    session = SecureChatSession()
    print("Starting secure chat session. Type '/exit' or '/quit' to end the session.")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["/exit", "/quit"]:
            quitEvent = SessionAuditEvent(
                model=AllowedModels.QWEN.value,
                input_chars=len(user_input),
                output_chars=len(session.get_context()),
                total_turns=len(session.messages),
                success=True,
                endpoint_type="local"
            )
            log_audit_event(quitEvent)
            break
        if user_input.lower() == "/clear":
            session.clear()
            print("Session cleared.")
            continue
        session.add_user_message(user_input)
        context = session.get_context()
        answer = query_local_llm(AllowedModels.QWEN, 0.2, 8000, False, context)
        messageEvent = SessionAuditEvent(
            model=AllowedModels.QWEN.value,
            input_chars=len(user_input),
            output_chars=len(answer),
            total_turns=len(session.messages),
            success=True,
            endpoint_type="local"
        )
        log_audit_event(messageEvent)
        session.add_assistant_message(answer)
        session.output_message(answer)
    
if __name__ == "__main__":
    app()
