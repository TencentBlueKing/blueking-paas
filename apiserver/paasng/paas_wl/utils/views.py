# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from blue_krill.web.std_error import APIError
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, ValidationError
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.response import Response
from rest_framework.views import exception_handler, set_rollback


def one_line_error(detail):
    """Extract one line error from error dict"""
    try:
        # A bare ValidationError will result in a list "detail" field instead of a dict
        if isinstance(detail, list):
            return detail[0]
        else:
            key, (first_error, *_) = next(iter(detail.items()))
            if key == 'non_field_errors':
                return first_error
            return f'{key}: {first_error}'
    except Exception:
        return '参数格式错误'


def custom_exception_handler(exc, context):
    # Use a standard error response instead of REST Framework's default behaviour
    #
    # {
    #   "code": "ERROR_CODE",
    #   "detail": "ERROR_DETAILS"                       # String
    #   "fields_detail": {"field1": ["error message"]}  # Only presents in ValidationError
    # }
    #
    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        # Return 401 status for unauthorized requests, downstream server might hijack and modify
        # this response to deliver extra information.
        data = {"detail": "Current request is unauthorized", "code": "UNAUTHORIZED"}
        return Response(data, status=status.HTTP_401_UNAUTHORIZED, headers={})
    if isinstance(exc, ValidationError):
        data = {'code': 'VALIDATION_ERROR', 'detail': one_line_error(exc.detail), 'fields_detail': exc.detail}
        set_rollback()
        return Response(data, status=exc.status_code, headers={})
    elif isinstance(exc, APIError):
        data = {'code': exc.code, 'detail': exc.message}
        set_rollback()
        return Response(data, status=exc.status_code, headers={})

    # Call REST framework's default exception handler to get the standard error response.
    response = exception_handler(exc, context)
    # Use a default error code
    if response is not None:
        response.data.update(code='ERROR')
    return response


class IgnoreClientContentNegotiation(BaseContentNegotiation):
    def select_parser(self, request, parsers):
        """
        Select the first parser in the `.parser_classes` list.
        """
        return parsers[0]

    def select_renderer(self, request, renderers, format_suffix):
        """
        Select the first renderer in the `.renderer_classes` list.
        """
        return (renderers[0], renderers[0].media_type)
