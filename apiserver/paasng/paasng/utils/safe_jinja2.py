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

# 以 sandbox 模式运行模板, 增强 jinja2 的安全性, 防注入漏洞

import os
import typing as t
from functools import partial

import jinja2
from jinja2.sandbox import SandboxedEnvironment


class NoCallableSandboxedEnvironment(SandboxedEnvironment):
    """A SandboxedEnvironment that does not allow any function calls."""

    def is_safe_callable(self, obj: t.Any) -> bool:
        return False


def _get_file_environment(
    searchpath: t.Union[str, "os.PathLike[str]", t.Sequence[t.Union[str, "os.PathLike[str]"]]],
    trim_blocks: bool = False,
):
    return SandboxedEnvironment(loader=jinja2.FileSystemLoader(searchpath), trim_blocks=trim_blocks)


FileEnvironment = _get_file_environment


_default_env = NoCallableSandboxedEnvironment()


def _safe_template(source, env_cls=NoCallableSandboxedEnvironment, *args, **kwargs):
    if not args and not kwargs:
        return _default_env.from_string(source)
    return env_cls(*args, **kwargs).from_string(source)


Template = _safe_template


# StrFormatCompatTemplate is a Template that uses a single brace `{}` as delimiters, which is
# compatible with str.format() and can be used as a replacement when the template is untrusted.
StrFormatCompatTemplate = partial(
    _safe_template,
    # Disable any function/method calls because supporting `obj.delete()` can be dangerous.
    env_cls=NoCallableSandboxedEnvironment,
    variable_start_string="{",
    variable_end_string="}",
)
