# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

"""How the API reports request validation failures.

Registered in `app_spark_api.api`::

    api = AppSparkNinjaAPI(title="App Spark API", urls_namespace="api")
    api.exception_handler(ValidationError)(partial(handle_validation_error, api=api))
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.utils.translation import gettext as _
from ninja import NinjaAPI
from ninja.errors import ValidationError, ValidationErrorContext

from app_spark_api.utils.api_errors.error_codes import error_codes

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

# Enough for the caller to see what to fix; `data` still lists every failure.
_MAX_SUMMARIZED_VALIDATION_ERRORS = 3


class AppSparkNinjaAPI(NinjaAPI):
    """A NinjaAPI whose validation errors locate fields the way the caller sent them.

    For ``POST /projects/-/create-from-prompt/`` with ``{"content": ""}``, the
    ``ValidationError.errors`` that ninja builds by default are::

        [{"type": "string_too_short", "loc": ("body", "payload", "content"),
          "msg": "String should have at least 1 character", "ctx": {"min_length": 1}}]

    and with this override::

        [{"loc": ("body", "content"), "msg": "String should have at least 1 character",
          "type": "string_too_short"}]
    """

    def validation_error_from_error_contexts(self, error_contexts: list[ValidationErrorContext]) -> ValidationError:
        """Build each error as ``{"loc", "msg", "type"}``, following django-ninja's documented override.

        Unlike the default, ``loc`` leaves out the view's parameter name when that parameter is the
        whole body: ninja reads such a body as ``{param: body}``, so the default reports a missing
        ``content`` at ``("body", "payload", "content")`` although the client never sends ``payload``.
        ``input`` and ``ctx`` are dropped too, ``msg`` already says what was expected.

        Ref: https://django-ninja.dev/guide/errors/ ("Customizing the errors list itself")
        """
        errors: list[dict[str, Any]] = []
        for context in error_contexts:
            model = context.model
            source = model.__ninja_param_source__
            flatten_map_reverse = getattr(model, "__ninja_flatten_map_reverse__", {})
            body_param = getattr(model, "__read_from_single_attr__", None)
            for error in context.pydantic_validation_error.errors(
                include_url=False, include_context=False, include_input=False
            ):
                loc = flatten_map_reverse.get(error["loc"], error["loc"])
                if body_param and loc[:1] == (body_param,):
                    loc = loc[1:]
                errors.append({"loc": (source, *loc), "msg": error["msg"], "type": error["type"]})
        return ValidationError(errors)


def handle_validation_error(request: HttpRequest, exc: ValidationError, api: NinjaAPI) -> HttpResponse:
    """Echo back which fields failed and why, both as one sentence and as a list.

    Unlike integration failures, a validation error only describes the caller's
    own request, so there is nothing to hide. The response is rendered by the
    ``APIError`` handler registered on ``api``, like every other failure.

    Ref: https://www.rfc-editor.org/rfc/rfc9457.html (a short ``detail`` plus a list of per-field errors)
    """
    error = error_codes.VALIDATION_ERROR.format()
    if summary := _summarize_validation_errors(exc.errors):
        # `format(summary)` would join with ": " after the default message's own full stop.
        error = error.format(_("Request validation failed: {summary}"), replace=True, summary=summary)
    return api.on_exception(request, error.set_data(exc.errors))


def _summarize_validation_errors(errors: list[dict[str, Any]]) -> str:
    """Join ``{"loc", "msg"}`` errors into one sentence, e.g. ``body.content: Field required``.

    Entries without a ``msg``, such as the ones ninja's pagination raises, are left to ``data``.
    """
    parts = [f"{_format_error_loc(error.get('loc', ()))}: {error['msg']}" for error in errors if "msg" in error]
    summary = "; ".join(parts[:_MAX_SUMMARIZED_VALIDATION_ERRORS])
    if len(parts) > _MAX_SUMMARIZED_VALIDATION_ERRORS:
        summary += f"; and {len(parts) - _MAX_SUMMARIZED_VALIDATION_ERRORS} more"
    return summary


def _format_error_loc(loc: tuple[str | int, ...]) -> str:
    """Render a pydantic ``loc`` as a path, e.g. ``("body", "items", 1, "name")`` -> ``body.items[1].name``.

    Ref: https://pydantic.dev/docs/validation/latest/errors/errors/ (``loc_to_dot_sep``)
    """
    path = ""
    for part in loc:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}" if path else part
    return path
