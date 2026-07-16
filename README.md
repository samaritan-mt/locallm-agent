# LocalSec Agent — CLI Ask

LocalSec Agent is a local-first macOS AI assistant designed for security engineers, DevSecOps workflows, and technical productivity.

The first feature, `localai ask`, provides a simple command-line interface to interact with a local language model running on your machine. It is built as the foundation for a future secured agent capable of reviewing Terraform, scanning repositories for secrets, explaining shell commands, and exposing controlled tools through Raycast and MCP.

The project is designed around three principles:

1. **Local-first execution** — prompts and responses stay on the machine by default.
2. **Security boundaries** — future tool execution must be policy-controlled and auditable.
3. **Developer workflow integration** — the assistant should be usable from the terminal, Raycast, and eventually MCP-compatible clients.

---

## Current Scope

This first version implements:

* A local CLI command: `localai ask`
* Integration with a local Ollama model
* Basic prompt submission
* Response rendering in the terminal
* Configurable model name and Ollama endpoint
* Project structure prepared for future tools, policy enforcement, and audit logging

This version does **not** execute shell commands, read arbitrary files, or access private system data.

---

## Example

```bash
localai ask "Explain Terraform rollback in one paragraph"
```

Example output:

```text
Terraform does not have a native rollback command. A rollback is usually performed by reverting the Terraform code to a previous known-good version, running terraform plan to inspect the impact, and then applying the corrected desired state. Remote state versioning can help recover from state corruption, but restoring old state should be treated as a last resort.
```

---

## Why This Project Exists

Most local AI assistants focus on convenience first and security later.

LocalSec Agent takes the opposite approach.

The goal is to build a local AI assistant that can eventually help with real security engineering tasks while enforcing clear boundaries around:

* file access
* shell execution
* secrets exposure
* command approval
* tool auditing
* prompt injection risks
* MCP tool permissions

The initial `ask` command is intentionally simple. It establishes the local inference layer before adding tools.

---

## Target Use Cases

Current use cases:

```bash
localai ask "Summarize the difference between SAST and DAST"
localai ask "Explain this command: find . -type f -name '*.tf'"
localai ask "What should I check during a Terraform security review?"
localai ask "Give me a checklist for secret remediation after a leaked AWS key"
```

Future use cases:

```bash
localai review-terraform ./infra
localai scan-secrets ./repo
localai explain-command "curl https://example.com/install.sh | sh"
localai repo-brief ./project
localai mcp serve
```

---

## Architecture

Current MVP architecture:

```text
Terminal
   |
   v
localai CLI
   |
   v
LLM Client
   |
   v
Ollama Local API
   |
   v
Local Model
```

Future architecture:

```text
Raycast / Terminal / MCP Client
        |
        v
LocalSec Agent CLI / API
        |
        +--> Local LLM Runtime
        |
        +--> Tool Router
        |       - filesystem tools
        |       - git tools
        |       - Terraform reviewer
        |       - secret scanner
        |       - command explainer
        |
        +--> Policy Engine
        |       - path allowlist
        |       - command allowlist
        |       - destructive-action confirmation
        |
        +--> Audit Logger
                - tool call history
                - approvals
                - blocked actions
```

---

## Requirements

### System

* macOS, preferably Apple Silicon
* Tested target: MacBook Pro M4 Pro
* Python 3.11+
* Ollama installed locally

### Recommended tools

```bash
brew install ollama
brew install uv
```

Or install Python dependencies with `pip` if `uv` is not used.

---

## Installing Ollama

Install Ollama:

```bash
brew install ollama
```

Start Ollama:

```bash
ollama serve
```

Pull a model:

```bash
ollama pull qwen2.5:7b
```

Other possible local models:

```bash
ollama pull llama3.1:8b
ollama pull mistral:7b
ollama pull deepseek-coder:6.7b
```

Recommended starting model:

```bash
qwen2.5:7b
```

It is fast enough for local CLI usage and good enough for technical explanations.

---

## Project Setup

Clone the repository:

```bash
git clone https://github.com/<your-username>/localsec-agent.git
cd localsec-agent
```

Create the Python environment:

```bash
uv venv
source .venv/bin/activate
```

Install dependencies:

```bash
uv pip install -e .
```

Or with pip:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

## Suggested Project Structure

```text
localsec-agent/
  README.md
  pyproject.toml

  src/
    localai/
      __init__.py
      main.py
      llm.py
      config.py

      tools/
        __init__.py

      policy/
        __init__.py

      audit/
        __init__.py

  tests/
    test_llm.py
    test_cli.py

  examples/
    prompts/
      terraform-rollback.txt
      secret-remediation.txt
```

---

## Minimal `pyproject.toml`

```toml
[project]
name = "localsec-agent"
version = "0.1.0"
description = "Local-first AI assistant for security engineering workflows"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.12.0",
    "rich>=13.0.0",
    "requests>=2.31.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0.0"
]

[project.scripts]
localai = "localai.main:app"
```

---

## Configuration

By default, the CLI expects Ollama to be available at:

```text
http://localhost:11434
```

Default model:

```text
qwen2.5:7b
```

Example configuration file:

```yaml
ollama:
  endpoint: "http://localhost:11434"
  model: "qwen2.5:7b"

agent:
  temperature: 0.2
  stream: false
```

Suggested path:

```text
~/.config/localsec-agent/config.yaml
```

---

## Usage

Basic prompt:

```bash
localai ask "What is least privilege in IAM?"
```

Technical explanation:

```bash
localai ask "Explain the security risks of using Action='*' and Resource='*' in an IAM policy"
```

Terraform help:

```bash
localai ask "What should I verify before applying Terraform changes in production?"
```

Incident response:

```bash
localai ask "A developer leaked an AWS access key in Git. Give me the remediation steps."
```

Command explanation:

```bash
localai ask "Explain this command and identify risks: curl https://example.com/install.sh | sh"
```

---

## Security Design

The initial `ask` command is read-only from the system perspective.

It sends only the prompt provided by the user to the local Ollama API.

It does not:

* execute commands
* read files automatically
* inspect environment variables
* access SSH keys
* access cloud credentials
* access macOS Keychain
* send data to external APIs

Future tools must follow a deny-by-default model.

---

## Future Permission Model

Future versions should include a policy file:

```yaml
allowed_paths:
  - "~/Projects"
  - "~/Documents/Notes"

blocked_paths:
  - "~/.ssh"
  - "~/.aws"
  - "~/.gnupg"
  - "~/Library/Keychains"
  - "~/Library/Messages"
  - "~/Library/Mail"

allowed_commands:
  - "ls"
  - "cat"
  - "grep"
  - "find"
  - "git"
  - "terraform"
  - "python3"
  - "jq"

blocked_patterns:
  - "rm -rf"
  - "sudo"
  - "curl .*\\|.*sh"
  - "chmod 777"
  - "aws configure"
  - "security find-generic-password"
```

Future destructive actions must require explicit confirmation.

---

## Audit Logging Roadmap

Future tool calls should generate local audit events:

```json
{
  "timestamp": "2026-01-01T10:00:00Z",
  "command": "review-terraform",
  "target": "~/Projects/demo-infra",
  "approved": true,
  "risk_level": "low"
}
```

Audit logs should never contain raw secrets.

---

## Development Roadmap

### Phase 1 — CLI Ask

* [x] Create CLI structure
* [x] Connect to Ollama
* [x] Implement `localai ask`
* [ ] Add config file support
* [ ] Add streaming output
* [ ] Add tests

### Phase 2 — Security Tools

* [ ] `localai explain-command`
* [ ] `localai scan-secrets`
* [ ] `localai review-terraform`
* [ ] `localai repo-brief`

### Phase 3 — Safety Controls

* [ ] Path allowlist
* [ ] Command allowlist
* [ ] Secret redaction
* [ ] Approval prompts
* [ ] Local audit logs

### Phase 4 — macOS Integration

* [ ] Raycast Script Command
* [ ] Raycast Extension
* [ ] macOS Shortcuts integration
* [ ] Clipboard summarization

### Phase 5 — MCP Integration

* [ ] MCP server mode
* [ ] Tool schemas
* [ ] Local-only binding
* [ ] Permission-aware tool execution

---

## Raycast Integration Preview

The first Raycast integration can be a Script Command:

```bash
#!/bin/bash
# @raycast.schemaVersion 1
# @raycast.title Ask LocalSec
# @raycast.mode fullOutput
# @raycast.argument1 { "type": "text", "placeholder": "Ask your local agent" }

localai ask "$1"
```

This allows triggering the local assistant directly from Raycast.

---

## Design Principles

### Local First

The assistant should run locally by default and avoid unnecessary external network calls.

### Least Privilege

Future tools should access only the minimum required data.

### Explicit Consent

Any operation that modifies files, runs commands, or accesses sensitive paths should require explicit approval.

### Auditability

Tool execution should be logged locally in a redacted and reviewable format.

### Security Engineering First

This is not a generic productivity chatbot. The long-term goal is to build a safe local assistant for security engineering workflows.

---

## Limitations

Current limitations:

* No tool execution
* No Raycast extension yet
* No MCP support yet
* No file review functionality yet
* No built-in prompt injection protection yet
* No secret redaction yet
* Depends on Ollama availability

These limitations are intentional for the first version.

The first milestone focuses on establishing a reliable local inference interface before adding tools and permissions.

---

## Example Portfolio Description

LocalSec Agent is a privacy-first macOS AI assistant for security engineers. It integrates local LLM inference with a CLI-first workflow and is designed to evolve into a secure tool-execution agent with policy controls, audit logging, Raycast integration, and MCP support.

---

## License

MIT License.

---

## Status

Early MVP.

Current focus:

```text
localai ask
```

Next focus:

```text
localai explain-command
localai scan-secrets
localai review-terraform
```
