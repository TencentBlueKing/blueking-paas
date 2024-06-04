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
from dataclasses import dataclass

from paas_wl.infras.resources.base.kres import KEvent
from paas_wl.infras.resources.kube_res.base import AppEntity

from .entities import InvolvedObject, Source
from .kres_slzs import EventDeserializer, EventSerializer


@dataclass
class Event(AppEntity):
    """应用事件

    :param reason: 事件产生的原因
    :param count: 事件发生的次数
    :param type: 事件的类型，常见类型有 "Normal" 和 "Warning"
    :param message: 事件发生的详细信息
    :param source: 报告该事件的组件，可以是进程或节点
    :param involved_object: 与该事件相关的对象
    """

    reason: str
    count: int
    type: str
    message: str
    first_timestamp: str
    last_timestamp: str
    source: Source
    involved_object: InvolvedObject

    class Meta:
        kres_class = KEvent
        deserializer = EventDeserializer
        serializer = EventSerializer
