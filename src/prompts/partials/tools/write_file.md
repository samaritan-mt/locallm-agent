You have access to the `write_file` tool. You can use it to write or overwrite text files in your local workspace.

**RULES:**
1. Use `write_file` whenever you need to create Python scripts, configuration files, or markdown reports.
2. Do not use bash shell commands (`echo`, `cat << EOF`) to create multi-line files; ALWAYS use `write_file`.
