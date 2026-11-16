#!/usr/bin/env bash
# Launch YAPAY VOLB from anywhere.
cd "$(dirname "$(readlink -f "$0")")" || exit 1
# Start with a clean Claude environment even when launched from a Claude Code / desktop terminal.
unset CLAUDECODE ANTHROPIC_BASE_URL ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN
exec .venv/bin/python main.py "$@"
