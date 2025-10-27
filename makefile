UV_PATH := $(shell which uv)

check:
	uv run ruff check && uv run pyright

install:
	pkill -f "Claude" || true
	uv pip compile pyproject.toml -o requirements.txt
	uv run fastmcp install claude-desktop main.py --project .
	# Replace "uv" with the full path to uv in the JSON config; this is since claude may not have the same PATH set
	sed -i '' 's|"command": "uv"|"command": "$(UV_PATH)"|' ~/Library/Application\ Support/Claude/claude_desktop_config.json
	open -a "Claude"


edit_claude:
	code ~/Library/Application\ Support/Claude/claude_desktop_config.json
