## Apple Notes assistant

This is an AI assistant for Apple Notes on macOS. It can list note titles, search
notes, read a selected note, summarize checklists or task lists, and create a new
note when explicitly asked. It can also search the live web for current information
and return source links. It can move one uniquely titled note to Recently Deleted
when explicitly asked. It cannot edit notes.

1. Add `OPENAI_API_KEY=...` to a `.env` file in this folder.
2. Run `uv run python notes.py`.
3. Ask something such as: `Find my shopping list and tell me what I need.`

## Project structure

```text
src/aiagents/
├── config.py          # Settings, .env loading, and project paths
├── notes_client.py    # macOS Apple Notes automation
├── agent.py           # OpenAI conversation and tool-calling loop
├── main.py            # Terminal application entry point
└── prompts/
    └── system_prompt.txt
```

`notes.py` remains as a short compatibility launcher. For a quick development
check of Notes access without calling the AI model, run `uv run python test.py`.

Web search is a hosted OpenAI tool configured in `agent.py`; it does not require a
separate browser driver or scraping library. Example: `Search today's weather in
Tbilisi and save a short summary in a note.`

The first Notes request may prompt you to allow your terminal (or IDE) to control
Notes. Approve it in **System Settings → Privacy & Security → Automation**.
