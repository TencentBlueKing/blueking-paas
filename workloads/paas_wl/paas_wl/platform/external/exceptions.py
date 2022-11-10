# -*- coding: utf-8 -*-


class PlatClientRequestError(Exception):
    """Error when requesting platform service"""


class PlatResponseError(PlatClientRequestError):
    """The response from platform service is invalid"""

    def __init__(self, message: str, status_code: int, response_text: str):
        self.message = message
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(message)

    def __str__(self) -> str:
        """Try to return a user-friendly string when 400 error occurred"""
        if self.status_code == 400:
            return f'{self.message}, response={self.response_text}'
        return self.message
