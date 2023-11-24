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
from blue_krill.data_types.enum import EnumField, StructuredEnum

# 注解或标签中存储进程名称的键名
PROCESS_NAME_KEY = "bkapp.paas.bk.tencent.com/process-name"
PROCESS_MAPPER_VERSION_KEY = "bkapp.paas.bk.tencent.com/process-mapper-version"

# The default maximum replicas for cloud-native apps's processes
# TODO: Use dynamic limitation for each app
DEFAULT_CNATIVE_MAX_REPLICAS = 10


class ProcessUpdateType(str, StructuredEnum):
    """Type of updating processes"""

    START = EnumField("start")
    STOP = EnumField("stop")
    # scale 提供调整副本数量 & 自动扩缩容能力
    SCALE = EnumField("scale")


class ProcessTargetStatus(str, StructuredEnum):
    """Choices of process status"""

    START = EnumField("start")
    STOP = EnumField("stop")


class ProbeType(str, StructuredEnum):
    """Choices of probe type"""

    READINESS = EnumField("readiness", label="readinessProbe")
    LIVENESS = EnumField("liveness", label="livenessProbe")
    STARTUP = EnumField("startup", label="startupProbe")
