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

import shlex
from typing import List, Optional

from pydantic import BaseModel, Field

from .utils import set_alias_field


class HookCmd(BaseModel):
    """The HookCmd describes a hook command."""

    command: Optional[List[str]] = Field(default_factory=list)
    args: Optional[List[str]] = Field(default_factory=list)

    def __init__(self, **data):
        # FIXME 处理 proc_command 与 command/args 的关系
        if proc_command := data.get("proc_command"):
            data["command"] = []
            data["args"] = shlex.split(proc_command)
        super().__init__(**data)


class Hooks(BaseModel):
    pre_release: HookCmd | None = None

    def __init__(self, **data):
        # db 旧数据使用了 camel case
        data = set_alias_field(data, "preRelease", to="pre_release")
        super().__init__(**data)
