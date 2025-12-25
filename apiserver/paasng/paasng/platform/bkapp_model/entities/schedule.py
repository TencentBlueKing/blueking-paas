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

from pydantic import BaseModel


class Toleration(BaseModel):
    """Kubernetes Toleration for pod scheduling

    :param key: The taint key that the toleration applies to.
    :param operator: The operator (Equal or Exists).
    :param value: The taint value the toleration matches to.
    :param effect: The taint effect to match (NoSchedule, PreferNoSchedule, NoExecute).
    :param toleration_seconds: The period of time the toleration tolerates the taint.
    """

    key: str | None = None
    operator: str | None = None
    value: str | None = None
    effect: str | None = None
    toleration_seconds: int | None = None


class Schedule(BaseModel):
    """Pod schedule config

    :param node_selector: Node selector for pod scheduling
    :param tolerations: Tolerations for pod scheduling
    """

    node_selector: dict[str, str] | None = None
    tolerations: list[Toleration] | None = None
