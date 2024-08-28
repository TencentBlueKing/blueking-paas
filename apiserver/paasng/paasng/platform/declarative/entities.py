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
from typing import Dict

from attrs import define, field

from paasng.platform.engine.models.deployment import ProcessTmpl


@define
class DeployHandleResult:
    """部署阶段处理应用描述文件的结果类。

    :param use_cnb: 是否使用了 v3 版本 CNB 模式，对 S-Mart 应用有意义
    :param processes: 本次处理的进程列表, 命令为 Procfile 的单字符串格式
    """

    use_cnb: bool
    processes: Dict[str, ProcessTmpl] = field(factory=dict)
