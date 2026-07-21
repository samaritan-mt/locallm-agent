import typer
from policy.config import AllowedModels
from llm import *
from audit.events import AskAuditEvent,SessionAuditEvent
from audit.logger import log_audit_event
from session import SecureChatSession
from tools.command import execute_os_command, write_file, read_file
from tools import schemas
import re


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
    print("Starting chat session. Type '/exit' or '/quit' to end the session.")
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
        
        output_chars = 0
        last_command_run = None
        while True:
            context = session.get_context()
            message = query_local_llm(AllowedModels.QWEN, 0.2, 8000000, False, context, [schemas.ollama_json_schema(), schemas.write_file_schema(), schemas.read_file_schema()])
            
            tool_calls = message.get('tool_calls')
            if tool_calls:
                tool_call = tool_calls[0]
                func = tool_call.get('function', {})
                tool_name = func.get('name', '')
                args = func.get('arguments', tool_call.get('args', {}))
                
                thought = args.get('thought')
                if thought:
                    typer.secho(f"Thinking...\n", fg=typer.colors.MAGENTA)
                    typer.secho(thought, fg=typer.colors.CYAN)
                
                if tool_name == "execute_os_command":
                    command_to_run = args.get('command', '')
                    
                    if not command_to_run.strip():
                        typer.secho("Agent provided an empty command. Intercepting...", fg=typer.colors.RED)
                        session.messages.append(message)
                        session.add_user_message("SYSTEM ERROR: You passed an empty command argument. Please provide a valid command.")
                        continue
                        
                    if command_to_run == last_command_run:
                        typer.secho("Agent attempted to loop the same command. Intercepting...", fg=typer.colors.RED)
                        # We inject a simulated tool message to break the loop
                        session.messages.append(message)
                        session.add_tool_message("Error: You just executed this exact same command and it produced no output. Do not run it again. If it generated a file, use cat to read it. If the task is done, conclude your response.")
                        continue
                    
                    # Store the assistant's tool call in history
                    session.messages.append(message)
                    
                    tool_result = execute_os_command(command_to_run)
                    last_command_run = command_to_run
                elif tool_name == "write_file":
                    filepath = args.get('filepath', '')
                    content = args.get('content', '')
                    session.messages.append(message)
                    tool_result = write_file(filepath, content)
                elif tool_name == "read_file":
                    filepath = args.get('filepath', '')
                    session.messages.append(message)
                    tool_result = read_file(filepath)
                else:
                    session.messages.append(message)
                    tool_result = f"Error: Unknown tool '{tool_name}'."

                if len(tool_result) > 8000000:
                    tool_result = summarize_tool_output(tool_result, str(context))
                
                session.add_tool_message(tool_result)
            else:
                final_answer = message.get('content', '')
                
                # 1. Catch hallucinated markdown tool calls (both python-style and JSON-style)
                pseudo_tool_match = re.search(r"(execute_os_command|write_file|read_file)\s*\(|\{\s*\"name\"\s*:\s*\"(execute_os_command|write_file|read_file)\"", final_answer)
                
                if pseudo_tool_match:
                    typer.secho("Agent hallucinated a markdown tool call. Intercepting...", fg=typer.colors.RED)
                    session.messages.append(message)
                    session.add_user_message("SYSTEM ERROR: You attempted to call a tool by writing pseudo-code in a markdown block. You MUST use the native JSON Tool Calling API. Do not write tool names in plain text. Try again.")
                    continue

                thought_match = re.search(r"<thought>(.*?)</thought>", final_answer, re.DOTALL)
                if thought_match:
                    typer.secho(f"Thinking...\n", fg=typer.colors.MAGENTA)
                    typer.secho(thought_match.group(1), fg=typer.colors.CYAN)
                    
                final_answer_clean = re.sub(r"<thought>.*?</thought>\s*", "", final_answer, flags=re.DOTALL).strip()
                
                if not final_answer_clean and final_answer:
                    # Model provided text (e.g. an unclosed tag) but it was stripped or empty. Prompt it to continue.
                    session.add_assistant_message(final_answer)
                    session.add_user_message("Please continue and provide your final text response or tool call.")
                    continue
                
                output_chars = len(final_answer_clean)
                session.add_assistant_message(final_answer)
                session.output_message(final_answer_clean)
                break
                
        messageEvent = SessionAuditEvent(
            model=AllowedModels.QWEN.value,
            input_chars=len(user_input),
            output_chars=output_chars,
            total_turns=len(session.messages),
            success=True,
            endpoint_type="local"
        )
        log_audit_event(messageEvent)
    
if __name__ == "__main__":
    app()
