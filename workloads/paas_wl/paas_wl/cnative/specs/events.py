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

from paas_wl.cnative.specs.models import EnvResourcePlanner
from paas_wl.platform.applications.struct_models import ModuleEnv
from paas_wl.resources.base.base import get_client_by_cluster_name
from paas_wl.resources.base.kres import KEvent


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
    return Event(
        name=kube_data["metadata"]["name"],
        type=kube_data["type"],
        reason=kube_data["reason"],
        message=kube_data["message"],
        count=int(kube_data["count"] or 0),
        involved_object=involved_object,
        first_seen=arrow.get(kube_data["firstTimestamp"]).datetime,
        last_seen=arrow.get(kube_data["lastTimestamp"]).datetime,
    )


def list_failed_events(env: ModuleEnv, dt: Optional[datetime.datetime]) -> List[Event]:
    """List all reason=Failed Events in 'env'

    :param env: 模块环境
    :param dt: datetime, Optional, filter events first seen after dt

    """
    planer = EnvResourcePlanner(env)
    all_events = []
    with get_client_by_cluster_name(planer.cluster.name) as client:
        ret = KEvent(client).ops_label.list(namespace=planer.namespace, labels={})
        for kube_data in ret.items:
            all_events.append(deserialize(kube_data))
    failed_events = [e for e in all_events if e.reason == "Failed"]
    if dt:
        failed_events = [e for e in failed_events if e.first_seen >= dt]
    return failed_events
