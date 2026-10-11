# LocaLLM Agent

LocaLLM Agent is a local-first macOS AI assistant for security engineers and DevSecOps workflows. It talks to local models through Ollama, so prompts and data stay on your machine by default. An opt-in OpenRouter provider is available for remote inference, behind explicit consent.

It offers two commands:

* `localai ask` — one-shot question to a local model.
* `localai agent` — a stateful chat REPL where the model can call tools (run commands, read files, write files) under policy checks, user approval, and audit logging.

Design principles:

1. **Local-first execution** — prompts, data, and responses stay on the machine unless you opt in to a remote provider.
2. **Security boundaries** — tool use is policy-controlled, approval-gated, and audited.
3. **Developer workflow integration** — it runs from the terminal.

---

## Requirements

* macOS (the audit logger uses native syslog)
* Python 3.11+
* [Ollama](https://ollama.com) running at `127.0.0.1:11434` with at least one allowed model pulled (default `qwen2.5:7b`)
* Docker, with a container named `locallm-sandbox` running, if you want command execution (see below)
* Optional: an [OpenRouter](https://openrouter.ai) API key for the remote provider

## Installation

```bash
python -m venv venv
source venv/bin/activate
pip install .
pip install openrouter httpx   # used by the OpenRouter provider; not yet declared in pyproject.toml
ollama pull qwen2.5:7b
```

This installs the `localai` entry point.

---

## `localai ask`

Sends a single prompt to a local Ollama model and prints the answer. It has no tools: it cannot run commands or read files.

```bash
localai ask "Explain Terraform rollback in one paragraph"
localai ask "SAST vs DAST?" --model mistral:7b --temperature 0.1
```

| Option | Default | Description |
| --- | --- | --- |
| `--model` | `qwen2.5:7b` | One of `qwen2.5:7b`, `llama3.1:8b`, `mistral:7b`, `deepseek-coder:6.7b` |
| `--temperature` | `0.2` | 0.0–1.0 |
| `--max-input-chars` | `8000` | Prompt size limit |
| `--allow-remote-endpoint` | off | Permit non-local Ollama endpoints |
| `--debug-log` | off | Opt in to logging full prompts (warned as dangerous) |

## `localai agent`

Starts an interactive chat session.

```bash
localai agent                          # chat, no command execution
localai agent --allow-execution        # enable shell execution in the Docker sandbox
localai agent --list-sessions          # list recent saved sessions
localai agent --session-id <id>        # resume a session
localai agent --debug-timing           # print per-turn latency
```

REPL commands: `/exit` or `/quit`, `/clear`, `/openrouter`, `/ollama`.

### Tools

| Tool | Behavior |
| --- | --- |
| `execute_os_command` | Runs `docker exec locallm-sandbox sh -c <command>` after you approve it. |
| `read_file` | Reads files inside the current working directory only. Detected secrets are redacted before the content reaches the model. |
| `write_file` | Writes files after you approve it. Intended for the working directory only. |

Tool calls are validated against their schemas. Malformed calls get a correction prompt, and repeated identical commands and pseudo-code tool calls are intercepted.

### Sessions

Conversations are saved as JSON in `~/.locallm/sessions/` after each turn and on Ctrl-C. Resume with `--session-id`. API keys are never written to session files.

### OpenRouter (opt-in)

`/openrouter` switches the session to a remote model (`nvidia/nemotron-3-nano-30b-a3b:free`).

* The key is read from `OPENROUTER_API_KEY` or prompted for, validated, and held in memory only.
* You must confirm that your prompts will leave your machine.
* Remote calls are capped at 15 per session and 4096 output tokens per call.
* `/ollama` switches back and discards the key.

---

## Security features

* **Policy config** (`src/policy/config.py`): model allowlist, localhost-only Ollama endpoint by default, and a `SessionPolicyConfig` whose capabilities all default to off.
* **Secret scanning** (`src/policy/secrets.py`): user input and file contents are scanned for AWS, GitHub, Slack, Anthropic, OpenAI keys, private keys, DB URLs, and generic tokens. You are warned and asked before sending flagged input. File reads are redacted. Audit logs are redacted.
* **Prompt-injection screening**: tool output matching known injection patterns is flagged and sanitized before it goes back to the model.
* **Approval prompts** for command execution and file writes.
* **Audit logging** (`src/audit/`): structured JSON events for ask, session, tool execution, provider switch, and remote call, written to macOS syslog (stream fallback elsewhere).
* **Composable prompts** (`src/prompts/`, `src/policy/prompts.py`): the system prompt is assembled from partials, with per-tool sections for the enabled tools.

## Project layout

```text
src/
  main.py            Typer CLI: ask, agent, help
  llm.py             Legacy direct Ollama calls (marked deprecated)
  llm_router.py      LLMRouter and the local Ollama provider
  session.py         SecureChatSession (history, system prompt)
  session_store.py   JSON session persistence
  providers/         OpenRouter provider
  policy/            config, secret scanning, prompt manager
  tools/             tool implementations, schemas, call validator
  audit/             audit events and logger
  prompts/           system prompt templates and partials
tests/               pytest suite
```

## Testing and CI

```bash
pytest
```

GitHub Actions (`.github/workflows/`) runs pytest on pushes and PRs to `main` and runs Snyk Code (SAST) and Snyk Open Source (SCA) scans. The Snyk scans need a `SNYK_TOKEN` secret. A second minimal test workflow also exists.

## Known limitations

* `--allow-execution` sets the session policy, but `execute_os_command` builds a fresh default `SessionPolicyConfig()` rather than using the session's. Command execution therefore returns a policy violation even when the flag is set. This needs fixing.
* The `locallm-sandbox` Docker container is not created by this repo. You must start it yourself.
* `write_file` and `read_file` check the workspace boundary with a string-prefix test on the resolved path, which is weaker than a real path-containment check.
* The `openrouter` and `httpx` dependencies are not listed in `pyproject.toml`.
* Policy flags other than `can_execute_commands` are not enforced yet, and `SessionPolicyConfig.is_allowed()` always returns `False`.
* Planned, not built: MCP tool permissions.
