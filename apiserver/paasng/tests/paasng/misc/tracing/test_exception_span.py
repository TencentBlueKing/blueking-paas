# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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

from unittest.mock import MagicMock, patch

from paasng.misc.tracing import exception_span
from paasng.misc.tracing.exception_span import record_exception_to_span
from paasng.utils.masked_curlify import MASKED_CONTENT


def test_record_exception_to_span():
    """异常写入 diagnostic 事件，且 password 等敏感局部变量在 LOCALS 中脱敏。"""
    span = MagicMock()
    span.is_recording.return_value = True
    # 运行时拼接，避免字面值出现在 SOURCE 片段里
    password = "foo"  # noqa: F841

    try:
        raise RuntimeError("oops")
    except RuntimeError as exc:
        with patch.object(exception_span.trace, "get_current_span", return_value=span):
            record_exception_to_span(exc)

    span.add_event.assert_called_once()
    attributes = span.add_event.call_args.kwargs["attributes"]
    assert attributes["exception.type"] == "RuntimeError"
    assert f"password = {MASKED_CONTENT}" in attributes["exception.message"]
