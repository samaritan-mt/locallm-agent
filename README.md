# LocaLLM Agent

LocaLLM Agent is a local-first macOS AI assistant designed for security engineers, DevSecOps workflows, and technical productivity. By leveraging local LLMs through Ollama, it ensures that your data and prompts never leave your machine.

The agent features a stateful chat REPL and can autonomously execute tools inside sandboxed Docker containers to securely analyze repositories, explain shell commands, and interact with the host system without compromising security.

The project is designed around three principles:

1. **Local-first execution** — prompts, data, and responses stay on the machine by default.
2. **Security boundaries** — tool execution is sandboxed, policy-controlled, and strictly audited.
3. **Developer workflow integration** — the assistant operates seamlessly from the terminal.

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


The agent command line interface (CLI) is built using Python's built-in `argparse` library, providing a user-friendly and flexible interface for interacting with the LocalLLM Agent.



