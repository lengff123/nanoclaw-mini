# Tool Usage Notes

Tool signatures are provided automatically via function calling.
This file documents non-obvious constraints and usage patterns.

## exec - Safety Limits

- Commands have a configurable timeout (default 60s)
- Dangerous commands are blocked (rm -rf, format, dd, shutdown, etc.)
- Output is truncated at 10,000 characters
- `restrictToWorkspace` config can limit file access to the workspace

## cron - Scheduled Reminders

- Use `action="add"` to create jobs, `action="list"` to inspect jobs, and `action="remove"` to delete them
- For one-time reminders, pass `at="YYYY-MM-DDTHH:MM:SS"`
- For recurring tasks, use either `every_seconds` or `cron_expr` (plus optional `tz`)
