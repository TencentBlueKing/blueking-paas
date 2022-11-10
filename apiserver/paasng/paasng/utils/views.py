# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import functools
import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

from blue_krill.web.drf_utils import stringify_validation_error
from blue_krill.web.std_error import APIError
from django.conf import settings
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, ValidationError
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.views import exception_handler, set_rollback

logger = logging.getLogger(__name__)


def one_line_error(error: ValidationError):
    """Extract one line error from ValidationError"""
    try:
        return stringify_validation_error(error)[0]
    except Exception:
        logger.exception('Error getting one line error from %s', error)
        return _('参数格式错误')


ERROR_CODE_HEADER = 'bkapi-error-code'
ERROR_CODE_NUM_HEADER = 'bkapi-error-code-num'


def make_unauthorized_json() -> Dict:
    """Make a static json response for unauthorized requests"""
    return {
        "code": "Unauthorized",
        "detail": "用户未登录或登录态失效，请使用登录链接重新登录",
        "login_url": {
            "full": settings.LOGIN_FULL,
            "simple": settings.LOGIN_SIMPLE,
        },
    }


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
        return Response(make_unauthorized_json(), status=status.HTTP_401_UNAUTHORIZED, headers={})

    elif isinstance(exc, ValidationError):
        data = {
            'code': 'VALIDATION_ERROR',
            'detail': one_line_error(exc),
            'fields_detail': exc.detail,
        }
        set_rollback()
        return Response(data, status=exc.status_code, headers={})
    elif isinstance(exc, APIError):
        data = {
            'code': exc.code,
            'detail': exc.message,
        }
        set_rollback()
        return Response(
            data,
            status=exc.status_code,
            # Put error code & code number into headers
            headers={
                ERROR_CODE_HEADER: exc.code,
                ERROR_CODE_NUM_HEADER: exc.code_num,
            },
        )
    elif isinstance(exc, OSError):
        # Extra logging for `OSError`, this indicates "uploading errors" or "no empty disk space".
        logger.exception("Unexpected OSError happened")

    # Call REST framework's default exception handler to get the standard error response.
    response = exception_handler(exc, context)
    # Use a default error code
    if response is not None:
        response.data.update(code='ERROR')
    return response


class HookChain:
    """为链式调用 hook 提供封装的工具类"""

    def __init__(self, hook: Callable[..., Response], pre_hook: Optional['HookChain'] = None):
        """
        :param hook: 当前的 hook 函数
        :param pre_hook: 上一步的 hook 函数
        """
        self.hook = hook
        self.pre_hook = pre_hook

    def __call__(self, response, view, request, *args, **kwargs) -> Response:
        if self.pre_hook:
            response = self.pre_hook(response, view, request, *args, **kwargs)
        return self.hook(response, view, request, *args, **kwargs)


def allow_resp_patch(view_func):
    """Use this decorator to make the response of a view function patch-able"""

    def register_resp_hook(hook_func: Callable):
        view_func._hook_resp_func = HookChain(hook_func, getattr(view_func, "_hook_resp_func", None))

    view_func.register_resp_hook = register_resp_hook

    @functools.wraps(view_func)
    def decorated(self, request, *args, **kwargs):
        resp = view_func(self, request, *args, **kwargs)

        # Apply hook function chains
        try:
            resp_hook_func = view_func._hook_resp_func
        except AttributeError:
            return resp
        else:
            resp = resp_hook_func(resp, self, request, *args, **kwargs)
            return resp

    return decorated


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


class EventStreamRender(BaseRenderer):
    media_type = 'text/event-stream'
    format = 'text'
    charset = 'utf-8'
    render_style = 'text'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class BkStandardApiJSONRenderer(JSONRenderer):
    """Renderer which wraps original JSON response with an extra layer.

    - Original: `{"foo": [1, 2]}`
    - Wrapped: `{"result": true, "code": 0, "data": {"foo": [1, 2]}, "message": ""}`
    """

    format = 'bk_std_json'

    _successful_code = 0
    _default_code = -1
    _default_error_message = 'Unknown error, please try again later'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        # Wrap response data on demand
        resp = renderer_context['response']
        if status.is_success(resp.status_code):
            data = self.wrap_successful(data, resp)
        elif status.is_client_error(resp.status_code) or status.is_server_error(resp.status_code):
            data = self.wrap_error(data, resp)
        # For status codes other than (2xx, 4xx, 5xx), do not wrap data
        return super().render(data, accepted_media_type=None, renderer_context=None)

    def wrap_successful(self, data: Any, resp: Response) -> Any:
        """Wrap successful response data"""
        return {'result': True, 'data': data, 'code': self._successful_code, 'message': ''}

    def wrap_error(self, data: Any, resp: Response) -> Any:
        """Wrap error response data

        TODO: Provide more specific code for special status codes, such as 404, 401 etc.
        """
        if not isinstance(data, dict):
            return {'result': False, 'data': data, 'code': self._default_code, 'message': self._default_error_message}

        message = data.pop('detail', self._default_error_message)
        # The numeric error code was stored in response headers
        error_code = int(resp.get(ERROR_CODE_NUM_HEADER, self._default_code))
        slug_error_code = data.pop("code", None)

        result = {'result': False, 'data': data, 'code': error_code, 'message': message}
        # Put the original non-numeric "code" into data when found
        if slug_error_code:
            result['code_slug'] = slug_error_code
        return result


def get_filepath(fp, parent_dir: Union[str, Path]) -> Path:
    """Get uploaded file's local path

    :param parent_dir: when the fp object only exists in memory, it will be exported to `parent_dir`
    """
    parent_path = Path(str(parent_dir))
    if hasattr(fp, "name") and hasattr(fp, "read"):
        path = parent_path / fp.name
        with open(path, "wb") as fh:
            fh.write(fp.read())
        return path
    raise TypeError("Invalid File Type")


def unwrap_partial(func):
    """unwrap functools.partial for getting the real method"""
    while isinstance(func, functools.partial):
        func = func.func
    return func


def permission_classes(permission_classes, policy: str = "replace"):
    """A decorator that gives support for having action-based permission_classes

    usage:
    from django.utils.decorators import method_decorator
    _permission_classes = <this decorator>

    @method_decorator(
        _permission_classes([]),
        name="action_c"
    )
    class ViewSet:
        permission_classes = [Baz]

        @_permission_classes([Foo])
        def action_a(self, request):
            assert self.permission_classes == [Foo]

        @_permission_classes([Bar], policy="merge")
        def action_b(self, request):
            assert self.permission_classes == [Bar, Baz]

        def action_c(self, request):
            assert self.permission_classes == []
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            # try to unwrap partial from method_decorator
            bound_method = unwrap_partial(func)
            if hasattr(bound_method, "__self__"):
                # when use permission_classes with django method_decorator, we can only get self from bound_method
                self = bound_method.__self__
            else:
                # when use permission_classes as a normal decorator, we can only get self from args[0]
                self = args[0]
            if policy == "merge":
                self.permission_classes = getattr(self, "permission_classes", []) + permission_classes
            else:
                self.permission_classes = permission_classes
            return func(*args, **kwargs)

        return wrapped

    return decorator
