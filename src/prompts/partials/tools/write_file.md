You have access to the `write_file` tool. You can use it to write or overwrite text files in your local workspace.

**RULES:**
1. Use `write_file` whenever you need to create Python scripts, configuration files, or markdown reports.
2. Do not use bash shell commands (`echo`, `cat << EOF`) to create multi-line files; ALWAYS use `write_file`.
3. `content` is the finished file, not a description of it. If asked to analyze, summarize, or report on something, `content` must contain the actual analysis/summary/report text - not your reasoning about how you plan to produce it, and not your `thought` argument restated with the same headings.
