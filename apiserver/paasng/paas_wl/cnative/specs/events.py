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
import datetime
from typing import List, Optional

import arrow
from attrs import define
from kubernetes.dynamic import ResourceInstance

from paas_wl.resources.base.kres import KEvent
from paas_wl.resources.utils.basic import get_client_by_app
from paasng.platform.applications.models import ModuleEnvironment


@define
class ObjectReference:
    api_version: str
    kind: str
    namespace: str
    name: str


@define
class Event:
    name: str
    type: str
    reason: str
    message: str
    count: int
    source_component: Optional[str]
    involved_object: Optional[ObjectReference]
    first_seen: datetime.datetime
    last_seen: datetime.datetime


def deserialize(kube_data: ResourceInstance) -> Event:
    """deserialize a kube resource to Event object"""
    involved_object = None
    if kube_data.get("involvedObject"):
        involved_object = ObjectReference(
            kind=kube_data["involvedObject"]["kind"],
            api_version=kube_data["involvedObject"]["apiVersion"],
            namespace=kube_data["involvedObject"]["namespace"],
            name=kube_data["involvedObject"]["name"],
        )

    source_component = None
    if source := kube_data.get("source"):
        source_component = source["component"]

    return Event(
        name=kube_data["metadata"]["name"],
        type=kube_data["type"],
        reason=kube_data["reason"],
        message=kube_data["message"],
        count=int(kube_data["count"] or 0),
        source_component=source_component,
        involved_object=involved_object,
        first_seen=arrow.get(kube_data["firstTimestamp"]).datetime,
        last_seen=arrow.get(kube_data["lastTimestamp"]).datetime,
    )


def list_events(env: ModuleEnvironment, dt: Optional[datetime.datetime]) -> List[Event]:
    """List all Events in 'env'

    :param env: 模块环境
    :param dt: datetime, Optional, filter events first seen after dt
    """
    all_events = []
    with get_client_by_app(env.wl_app) as client:
        ret = KEvent(client).ops_label.list(namespace=env.wl_app.namespace, labels={})
        for kube_data in ret.items:
            all_events.append(deserialize(kube_data))
    if dt:
        all_events = [e for e in all_events if e.first_seen >= dt]
    return all_events
