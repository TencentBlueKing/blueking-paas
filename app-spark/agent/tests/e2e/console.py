"""A running commentary of what a live test is doing.

Under a plain run this is invisible. Under ``pytest -m live -s`` it is the point: a single turn
spends tens of seconds inside a real model, so a test that printed nothing would be
indistinguishable from a hang -- and when one does fail, the transcript above the failure is
usually what explains it.

The direction of every line is readable at a glance: ``>`` is what the client sent, ``<`` is
what the Runtime sent back. Nothing in this module ever fails a test; it only reports.
"""

import sys
from typing import Any

# Long enough to recognise a tool call or a file, short enough that one line stays one line.
CLIP = 110

INDENT = "    "

# The event stream is AG-UI, so its field names are camelCase -- unlike everything the Runtime
# itself emits. See ``README.md``.
THINKING_DELTAS = frozenset({"THINKING_TEXT_MESSAGE_CONTENT", "REASONING_MESSAGE_CONTENT"})
MESSAGE_ENDS = frozenset({"TEXT_MESSAGE_END", "THINKING_TEXT_MESSAGE_END", "REASONING_MESSAGE_END"})


def write(text: str) -> None:
    """Write without a newline and flush, so a streamed line grows as the tokens arrive."""
    sys.stdout.write(text)
    sys.stdout.flush()


def line(text: str = "") -> None:
    """Write one whole line."""
    write(f"{text}\n")


def banner(text: str) -> None:
    """Announce a new Runtime or a new phase of the scenario."""
    line()
    line(f"=== {text}")


def note(text: str) -> None:
    """Report something about the Runtime itself rather than a request."""
    line(f"{INDENT}| {text}")


def request(call: str, summary: str = "") -> None:
    """Announce a request whose response will take a while to arrive."""
    line(f"{INDENT}{call}  {summary}".rstrip())


def exchange(call: str, status: int, summary: str = "") -> None:
    """Report one finished request as the client saw it."""
    line(f"{INDENT}{call} -> {status}  {summary}".rstrip())


def clip(text: str, limit: int = CLIP) -> str:
    """Return ``text`` as a single line, shortened to something a console can show."""
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else f"{flat[:limit]}..."


class StreamPrinter:
    """Render one run's AG-UI events on the console while the run is still going.

    Text and reasoning are written token by token, because watching them appear is the only way
    to tell a slow model from a stuck one. Tool traffic is buffered until its end event and then
    printed on one clipped line instead: the arguments can carry a whole file, which is worth
    seeing the shape of and not worth scrolling through.
    """

    def __init__(self) -> None:
        self._open: str | None = None
        self._names: dict[str, str] = {}
        self._args: dict[str, list[str]] = {}

    def feed(self, event: dict[str, Any]) -> None:
        """Show one event."""
        kind = str(event.get("type"))
        if kind == "TEXT_MESSAGE_CONTENT":
            self._grow("model", str(event["delta"]))
        elif kind in THINKING_DELTAS:
            self._grow("think", str(event["delta"]))
        elif kind in MESSAGE_ENDS:
            self.close()
        elif kind == "TOOL_CALL_START":
            call_id = str(event["toolCallId"])
            self._names[call_id] = str(event["toolCallName"])
            self._args[call_id] = []
        elif kind == "TOOL_CALL_ARGS":
            self._args.setdefault(str(event["toolCallId"]), []).append(str(event["delta"]))
        elif kind == "TOOL_CALL_END":
            self.close()
            call_id = str(event["toolCallId"])
            name = self._names.pop(call_id, "?")
            line(f"{INDENT}tool > {name} {clip(''.join(self._args.pop(call_id, [])))}")
        elif kind == "TOOL_CALL_RESULT":
            self.close()
            line(f"{INDENT}tool < {clip(str(event.get('content', '')))}")
        elif kind == "RUN_ERROR":
            self.close()
            line(f"{INDENT}error < {clip(str(event.get('message', event)))}")

    def close(self) -> None:
        """Finish whatever line the stream left open."""
        if self._open is not None:
            line()
            self._open = None

    def _grow(self, channel: str, delta: str) -> None:
        if self._open != channel:
            self.close()
            write(f"{INDENT}{channel} < ")
            self._open = channel
        # A model that answers in paragraphs must not break the left margin of the transcript.
        write(delta.replace("\n", f"\n{INDENT}       "))
