"""The OpenAI Responses agent that uses Apple Notes and live web search."""

import json  # Parses the model's JSON function arguments.
from collections.abc import Callable  # Describes the optional tool-status callback.
from typing import Any  # Describes API data with multiple possible shapes.

from openai import OpenAI  # The official OpenAI Python client.

from .config import Settings  # Holds the model name, API key, and prompt path.
from .notes_client import AppleNotesClient  # Provides the local Apple Notes actions.


class NotesAgent:
    """Keep a conversation and give the model access to web and Notes tools."""

    def __init__(
        self,
        settings: Settings,
        notes: AppleNotesClient,
        confirm_delete: Callable[[str], bool],
        on_tool_call: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        # Create the authenticated client that talks to the OpenAI API.
        self.client = OpenAI(api_key=settings.api_key)
        # Save the configured model so every request uses the same model.
        self.model = settings.model
        # Save the local client that carries out only approved Notes actions.
        self.notes = notes
        # Require the terminal user's approval before calling the delete method.
        self.confirm_delete = confirm_delete
        # Let the terminal UI display tool activity without using plain print().
        self.on_tool_call = on_tool_call
        # Read the instructions once when the program starts.
        self.instructions = settings.prompt_file.read_text(encoding="utf-8")
        # Keep a simple local history for learning/debugging and future UI work.
        self.messages: list[dict[str, str]] = [
            {"role": "system", "content": self.instructions}
        ]
        # Responses API uses this ID to remember the prior server-side turn.
        self.previous_response_id: str | None = None

    def ask(self, question: str) -> str:
        """Answer one question, using web search or Apple Notes when useful."""
        # Save the user's question in our local, human-readable history.
        self.messages.append({"role": "user", "content": question})

        # Start a Responses API turn. Web search runs on OpenAI's side.
        response = self.client.responses.create(
            model=self.model,
            instructions=self.instructions,
            input=question,
            previous_response_id=self.previous_response_id,
            tools=self._tools(),
            reasoning={"effort": "none"},
        )

        # The model may need local Notes functions after it searches the web.
        while function_calls := [
            item for item in response.output if item.type == "function_call"
        ]:
            tool_outputs = []
            for call in function_calls:
                # Run the local function requested by the model.
                result = self._run_tool(call.name, call.arguments)
                # Responses API needs the result linked to the original call ID.
                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": result,
                    }
                )

            # Give the function results back to the model so it can continue.
            response = self.client.responses.create(
                model=self.model,
                instructions=self.instructions,
                input=tool_outputs,
                previous_response_id=response.id,
                tools=self._tools(),
                reasoning={"effort": "none"},
            )

        # Save the completed turn ID so the next user question has context.
        self.previous_response_id = response.id
        answer = self._add_source_links(response, response.output_text)
        # Store the final answer locally, alongside the original question.
        self.messages.append({"role": "assistant", "content": answer})
        return answer

    def _run_tool(self, name: str, raw_arguments: str) -> str:
        """Validate model arguments and call the matching local Notes method."""
        # This allow-list prevents the model from calling arbitrary Python code.
        tools = {
            "list_notes": self.notes.list_notes,
            "read_note": self.notes.read_note,
            "search_notes": self.notes.search_notes,
            "create_note": self.notes.create_note,
            "update_note": self.notes.update_note,
            "delete_note": self.notes.delete_note,
        }
        tool = tools.get(name)
        if tool is None:
            return json.dumps({"error": f"Unknown tool: {name}"})

        try:
            # Convert the model's JSON string into Python keyword arguments.
            arguments = json.loads(raw_arguments or "{}")
            if name == "delete_note":
                title = arguments.get("title") if isinstance(arguments, dict) else None
                if not isinstance(title, str) or not title.strip():
                    return json.dumps({"error": "delete_note requires a nonempty title."})
                if not self.confirm_delete(title):
                    return json.dumps({"title": title, "message": "Deletion cancelled by the user."})
            # Tell the terminal UI which local Notes action is now running.
            if self.on_tool_call:
                self.on_tool_call(name, arguments)
            else:
                print(f"  [Apple Notes] {name}({arguments})")
            return tool(**arguments)
        except (json.JSONDecodeError, TypeError) as error:
            # Give the model a structured error it can respond to gracefully.
            return json.dumps({"error": f"Invalid tool arguments: {error}"})

    @staticmethod
    def _tools() -> list[dict[str, Any]]:
        """Return one hosted web tool plus the local Apple Notes function tools."""
        return [
            # OpenAI runs this hosted tool and returns current, cited web information.
            {"type": "web_search", "search_context_size": "medium"},
            # The following tools run locally in this Python application.
            {"type": "function", "name": "list_notes", "description": "List the user's Apple Notes titles and modification dates. Use it to discover a note before reading it.", "parameters": {"type": "object", "properties": {}}, "strict": False},
            {"type": "function", "name": "read_note", "description": "Read a single Apple Note by its exact title. Use list_notes or search_notes first when uncertain.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}, "strict": False},
            {"type": "function", "name": "search_notes", "description": "Search Apple Notes by words in their title or body. It returns matching titles and text, useful for finding lists and tasks.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}, "strict": False},
            {"type": "function", "name": "create_note", "description": "Create a new Apple Note in the default folder. Use only when the user explicitly asks to create a note.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "content": {"type": "string"}}, "required": ["title", "content"]}, "strict": False},
            {"type": "function", "name": "update_note", "description": "Replace the body of one uniquely titled Apple Note, optionally renaming it. Use only when the user explicitly asks to edit or modify that note. Read the note first, and use its exact title.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "content": {"type": "string"}, "new_title": {"type": "string", "description": "Optional replacement title."}}, "required": ["title", "content"]}, "strict": False},
            {"type": "function", "name": "delete_note", "description": "Move exactly one Apple Note with a unique exact title to Recently Deleted. Use only when the user explicitly asks to delete that note.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}, "strict": False},
        ]

    @staticmethod
    def _value(item: Any, name: str, default: Any = None) -> Any:
        """Read a field from either an SDK object or a dictionary."""
        return item.get(name, default) if isinstance(item, dict) else getattr(item, name, default)

    def _add_source_links(self, response: Any, answer: str) -> str:
        """Append clickable web-search source links when the API returns citations."""
        sources: list[tuple[str, str]] = []
        for item in response.output:
            if self._value(item, "type") != "message":
                continue
            for content in self._value(item, "content", []):
                for annotation in self._value(content, "annotations", []) or []:
                    citation = self._value(annotation, "url_citation")
                    url = self._value(citation, "url") if citation else None
                    title = self._value(citation, "title") if citation else None
                    if url and (title or url) not in sources:
                        sources.append((title or url, url))

        if not sources:
            return answer

        # Terminal users can open these Markdown links after a web-search answer.
        links = "\n".join(f"- [{title}]({url})" for title, url in sources)
        return f"{answer}\n\nSources:\n{links}"
