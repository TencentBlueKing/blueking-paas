# -*- coding: utf-8 -*-


class OtelServiceError(Exception):
    """This error indicates that there's something wrong when operating otel's
    API Gateway resource. It's a wrapper class of API SDK's original exceptions
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class OtelApiError(OtelServiceError):
    """When calling the otel api, otel returns an error message,
    which needs to be captured and displayed to the user on the page
    """
