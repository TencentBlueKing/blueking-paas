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
from dataclasses import dataclass
from typing import Dict


@dataclass
class VarsRenderContext:
    """The context for rendering environment variables.

    :param process_type: The type of the process, e.g. "web", "worker".
    """

    process_type: str


def render_vars_dict(d: Dict[str, str], context: VarsRenderContext) -> Dict[str, str]:
    """Render an environment variable dict, replace all supported variables with
    values in the given context.

    :param d: The environment variable dict to be rendered.
    :param context: The context for rendering.
    :return: The rendered environment variable dict. The original dict is not modified.
    """
    # Use a whitelist to avoid unexpected variable replacement
    _supported_key_suffixes = {"_LOG_NAME_PREFIX", "_PROCESS_TYPE"}
    result = d.copy()
    for k, v in d.items():
        if not any(k.endswith(suffix) for suffix in _supported_key_suffixes):
            continue

        # TODO: Use regular expression or other methods to replace variables when
        # there are more variables to be supported.
        result[k] = v.replace("{{bk_var_process_type}}", context.process_type)
    return result
