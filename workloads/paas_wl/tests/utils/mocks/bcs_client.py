# -*- coding: utf-8 -*-
from typing import Any, Dict, Optional

from bkapi_client_core.apigateway import Operation
from django.utils.crypto import get_random_string
from requests import Response

from paas_wl.resources.base.bcs_client import BCSClient


class StubBCSClient(BCSClient):
    def handle_request(self, operation: Operation, context: Dict[str, Any]) -> Optional[Response]:
        return Response()

    def parse_response(self, operation: Operation, response: Optional[Response]) -> Any:
        if operation.name == 'create_web_console_sessions':
            session_id = get_random_string(32)
            return {
                'code': 0,
                'data': {
                    'session_id': session_id,
                    'web_console_url': f'http://example.com/web_console/'
                    f'?session_id={session_id}&container_name={get_random_string(8)}',
                },
            }
        return {}
