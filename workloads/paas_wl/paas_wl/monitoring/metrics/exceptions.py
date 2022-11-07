# -*- coding: utf-8 -*-


class RequestMetricBackendError(Exception):
    """got exception during requesting to prometheus"""

    def __init__(self, resp):
        self.response = resp
        self.status_code = resp.status_code
        try:
            self.json_response = resp.json()
        except Exception:
            self.json_response = {}
        self.error_code = self.get_error_code()
        self.error_message = self.get_error_message()

    def get_error_code(self):
        return self.json_response.get('code', 'UNKNOWN')

    def get_error_message(self):
        return self.json_response.get('detail', 'Response is not a valid JSON')

    def __str__(self):
        return 'status_code=%s error_code=%s %s' % (self.status_code, self.error_code, self.error_message)
