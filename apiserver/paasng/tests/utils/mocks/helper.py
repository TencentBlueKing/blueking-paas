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
from contextlib import ExitStack, contextmanager
from typing import Any, Callable, Optional, Set, Type
from unittest import mock

_default_whitelist: Set[str] = {"__init__", "__class__", "__dict__", "__new__"}


@contextmanager
def patch_class_with_stub(
    class_: Type, stub: Any, default_filling: Callable = mock.MagicMock, whitelist: Optional[Set[str]] = None
):
    """patch a class with a """
    stack = ExitStack()
    whitelist = whitelist or _default_whitelist
    for attr_name in dir(class_):
        if attr_name in whitelist:
            continue
        if hasattr(stub, attr_name):
            stack.enter_context(mock.patch.object(class_, attr_name, side_effect=getattr(stub, attr_name)))
        else:
            stack.enter_context(mock.patch.object(class_, attr_name, side_effect=default_filling))
    with stack:
        yield
