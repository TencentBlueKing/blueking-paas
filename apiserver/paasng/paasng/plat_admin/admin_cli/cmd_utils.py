import sys
from typing import Any


class CommandBasicMixin:
    """Provide some basic functionalities for adm cli commands"""

    style: Any

    def exit_with_error(self, message: str, code: int = 2):
        """Exit execution and print error message"""
        self.print(self.style.NOTICE(f"Error: {message}"))
        sys.exit(2)

    def print(self, message: str, title: str = "") -> None:
        """A simple wrapper for print function, can be replaced with other implementations

        :param message: The message to be printed
        :param title: Use this title to distinguish different print messages
        """
        if title:
            print(self.style.SUCCESS(f"[{title.upper()}] ") + message)
        else:
            print(message)
