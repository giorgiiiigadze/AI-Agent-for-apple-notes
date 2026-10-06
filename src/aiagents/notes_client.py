"""A small client for reading and creating notes with macOS Automation."""

import json  # Converts Python data to/from JSON for JXA and tool responses.
import subprocess  # Runs macOS's built-in osascript command.
from typing import Any  # Describes values whose type is only known at runtime.


class AppleNotesClient:
    """Talk to the native Apple Notes app through JavaScript for Automation."""

    def __init__(self, max_notes: int = 100) -> None:
        # Save the maximum number of notes every method is allowed to return.
        self.max_notes = max_notes

    def list_notes(self) -> str:
        """Return note titles and modification dates without their bodies."""
        # Build a "list" script, run it in macOS, then format its result as JSON.
        return self._as_json(self._run_jxa(self._notes_script("list")))

    def read_note(self, title: str) -> str:
        """Return one note by title, ignoring capitalization."""
        # Pass the title separately so it is data, never JavaScript source code.
        return self._as_json(self._run_jxa(self._notes_script("read"), title))

    def search_notes(self, query: str) -> str:
        """Return notes whose title or text contains the search query."""
        # The JXA search action receives the user's search phrase as an argument.
        return self._as_json(self._run_jxa(self._notes_script("search"), query))

    def create_note(self, title: str, content: str) -> str:
        """Create a plain-text note in the user's default Notes folder."""
        # Send title and content as independent arguments to the JXA script.
        return self._as_json(self._run_jxa(self._notes_script("create"), title, content))

    def delete_note(self, title: str) -> str:
        """Delete one uniquely titled note, moving it to Recently Deleted."""
        # The JXA script rejects missing and duplicate titles before it deletes.
        return self._as_json(self._run_jxa(self._notes_script("delete"), title))

    @staticmethod
    def _as_json(result: Any) -> str:
        """Give tool calls a JSON string, including non-ASCII note text."""
        # ensure_ascii=False keeps characters such as ქართული readable.
        return json.dumps(result, ensure_ascii=False)

    def _run_jxa(self, script: str, *arguments: str) -> Any:
        """Execute a JXA script and parse its JSON response."""
        # -l JavaScript selects JXA; -- separates code from normal arguments.
        command = ["osascript", "-l", "JavaScript", "-e", script, "--", *arguments]
        try:
            # Run the Apple Notes command and collect standard output as text.
            completed = subprocess.run(command, capture_output=True, text=True, check=True)
            # Every JXA action returns JSON so Python can work with dictionaries/lists.
            return json.loads(completed.stdout)
        except FileNotFoundError:
            # This happens when the program runs somewhere other than macOS.
            return {"error": "Apple Notes access requires macOS (osascript was not found)."}
        except subprocess.CalledProcessError as error:
            # Return Notes permissions and automation errors in a tool-friendly format.
            detail = error.stderr.strip() or error.stdout.strip() or "Unknown AppleScript error"
            return {"error": f"Could not access Apple Notes: {detail}"}
        except json.JSONDecodeError:
            # Guard against an automation script that produced invalid JSON.
            return {"error": "Apple Notes returned an unexpected response."}

    def _notes_script(self, action: str) -> str:
        """Build the JXA program for one supported Apple Notes action."""
        return f'''\
            // Create a JXA reference to the installed macOS Notes application.
            const app = Application("Notes");
            // Read the command line values passed by Python after --.
            const argv = $.NSProcessInfo.processInfo.arguments;
            // Python supplies this trusted action name: list, read, search, create, or delete.
            const action = {json.dumps(action)};
            // Copy command-line values into a normal JavaScript array.
            const userArgs = [];
            for (let index = 6; index < argv.count; index++) {{
            userArgs.push(ObjC.unwrap(argv.objectAtIndex(index)));
            }}
            // The first argument is a title or search text; the second is note content.
            const query = userArgs[0] || "";
            const content = userArgs[1] || "";
            // Request the user's Notes collection from the native app.
            const notes = app.notes();
            // Notes stores bodies as HTML, so convert returned bodies to readable text.
            const clean = value => String(value || "").replace(/<[^>]*>/g, " ").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/\\s+/g, " ").trim();
            // Escape text before placing it into the HTML body of a newly created note.
            const escapeHtml = value => String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;").replace(/\\n/g, "<br>");
            // This variable will become the JSON response sent back to Python.
            let result;
            if (action === "list") {{
            // Return lightweight note metadata without reading every body.
            result = notes.slice(0, {self.max_notes}).map(note => ({{ title: String(note.name()), modified: String(note.modificationDate()) }}));
            }} else if (action === "read") {{
            // Locate one title without treating uppercase/lowercase as different.
            const note = notes.find(item => String(item.name()).toLowerCase() === query.toLowerCase());
            // Return either the selected note or a helpful not-found error.
            result = note ? {{ title: String(note.name()), body: clean(note.body()), modified: String(note.modificationDate()) }} : {{ error: `No note found with the title "${{query}}".` }};
            }} else if (action === "create") {{
            // Prevent creation of a note with no title or content.
            if (!query || !content) {{
                result = {{ error: "A note needs both a title and content." }};
            }} else {{
                // Create a Notes object with an HTML body made from safe plain text.
                const note = app.Note({{ name: query, body: `<div>${{escapeHtml(content)}}</div>` }});
                // Put the new note into the default account and default folder.
                app.defaultAccount.defaultFolder.notes.push(note);
                result = {{ title: String(note.name()), message: "Note created successfully." }};
            }}
            }} else if (action === "delete") {{
            // Match exactly so a broad search phrase can never delete several notes.
            const matches = notes.filter(item => String(item.name()).toLowerCase() === query.toLowerCase());
            if (matches.length === 0) {{
                result = {{ error: `No note found with the title "${{query}}".` }};
            }} else if (matches.length > 1) {{
                // Refuse ambiguous titles: the user must rename a note before retrying.
                result = {{ error: `Found ${{matches.length}} notes named "${{query}}". Delete requires a unique title.` }};
            }} else {{
                const deletedTitle = String(matches[0].name());
                // Notes treats this as a normal deletion and moves the note to Recently Deleted.
                app.delete(matches[0]);
                result = {{ title: deletedTitle, message: "Note moved to Recently Deleted." }};
            }}
            }} else {{
            // Lowercase the phrase so search is case-insensitive.
            const needle = query.toLowerCase();
            // Look through titles and bodies, then limit the number of matches.
            result = notes.map(note => ({{ title: String(note.name()), body: clean(note.body()), modified: String(note.modificationDate()) }}))
                .filter(note => note.title.toLowerCase().includes(needle) || note.body.toLowerCase().includes(needle))
                .slice(0, {self.max_notes});
            }}
            // Print JSON because Python reads the script's standard output.
            JSON.stringify(result);
        '''
