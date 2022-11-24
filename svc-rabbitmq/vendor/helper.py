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
import json
import logging
import random
import typing
from collections import namedtuple
from dataclasses import dataclass
from operator import attrgetter

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from paas_service.base_vendor import InstanceData
from paas_service.models import ServiceInstance

from .client import Client
from .models import Cluster, InstanceBill, Tag

if typing.TYPE_CHECKING:
    from django.db.models import QuerySet

logger = logging.getLogger(__name__)


@dataclass
class TaggedModelHelper:
    tags: 'typing.Union[QuerySet, typing.List[Tag]]'

    def as_dict(self):
        """Make tags as dict"""
        tags = {}
        for i in self.tags:
            tags[i.key] = i.value
        return tags

    def clear(self):
        """Clear all tags"""
        self.tags.delete()

    def set(self, key: 'str', value: 'str', **defaults) -> 'Tag':
        """Update or create a tag by key, must pass default values"""
        defaults["key"] = key
        tag, _ = self.tags.update_or_create(defaults=defaults, value=value)
        return tag

    def get(self, key: 'str', **values) -> 'typing.Optional[Tag]':
        """Get tag by key"""
        try:
            return self.tags.get(key=key, **values)
        except ObjectDoesNotExist:
            return None

    def delete(self, key: 'str', **values):
        """Delete a tag by key"""
        self.tags.filter(key=key, **values).delete()


@dataclass
class ClusterSelectStrategy:
    selector: 'ClusterSelector'
    clusters: 'typing.List[Cluster]'

    def assess(self) -> 'typing.List[Assessment]':
        """评估各个集群的分数"""
        raise NotImplementedError


class ClusterRandomStrategy(ClusterSelectStrategy):
    """随机选择"""

    def assess(self) -> 'typing.List[Assessment]':
        """评估各个集群的分数"""
        assessments = []
        for cluster in self.clusters:
            client = Client.from_cluster(cluster)
            if client.alive():
                score = random.randint(1, 100)
            else:
                score = 0
            assessments.append(Assessment(score=score, cluster=cluster))
        return assessments


Assessment = namedtuple("Assessment", ["score", "cluster"])
DefaultClusterStrategy = ClusterRandomStrategy


@dataclass
class ClusterSelector:
    strategy: 'typing.Type[ClusterSelectStrategy]'
    clusters: 'typing.Union[QuerySet, typing.List[Cluster]]'

    def assess(self) -> 'typing.List[Assessment]':
        """评估各个集群的分数"""
        clusters = list(self.clusters)
        strategy = self.strategy(self, clusters)
        assessments = sorted((i for i in strategy.assess() if i.score > 0), key=attrgetter("score"), reverse=True)
        return assessments

    def one(self) -> 'typing.Optional[Cluster]':
        """选择最高分的一个集群"""
        assessments = self.assess()
        if not assessments:
            return None
        return assessments[0].cluster


@dataclass
class InstanceHelper:
    instance: 'typing.Union[InstanceData, ServiceInstance]'

    @dataclass
    class Credentials:
        host: 'str'
        port: 'int'
        user: 'str'
        password: 'str'
        vhost: 'str'

    @classmethod
    def create_instance_data(
        cls, cluster: 'Cluster', bill: 'InstanceBill', virtual_host: 'str', user: 'str', password: 'str'
    ) -> 'InstanceData':
        return InstanceData(
            credentials={
                "host": cluster.host,
                "port": cluster.port,
                "user": user,
                "password": password,
                "vhost": virtual_host,
            },
            config={"cluster": cluster.id, "bill": bill.uuid.hex},
        )

    @classmethod
    def get_instance(cls, instance_id: 'str') -> 'ServiceInstance':
        return ServiceInstance.objects.get(pk=instance_id)

    @classmethod
    def from_db(cls, instance_id: 'str'):
        return cls(cls.get_instance(instance_id))

    def get_credentials(self) -> 'Credentials':
        credentials = self.instance.credentials
        if not isinstance(credentials, dict):
            credentials = json.loads(credentials)
        return self.Credentials(**credentials)

    def get_cluster_id(self) -> 'int':
        return self.instance.config.get("cluster", settings.INSTANCE_DEFAULT_CLUSTER_ID)

    def get_cluster(self) -> 'Cluster':
        return Cluster.objects.get(pk=self.get_cluster_id())

    def get_bill(self) -> 'InstanceBill':
        bill, _ = InstanceBill.objects.get_or_create(pk=self.instance.config["bill"])
        return bill

    def get_client(self) -> 'Client':
        cluster = self.get_cluster()
        return Client.from_cluster(cluster)


class Version:
    def __init__(self, version: 'str'):
        self.version = version
        self.parts = tuple(version)

    def __eq__(self, other: 'Version'):
        return self.parts == other.parts

    def __ne__(self, other: 'Version'):
        return self.parts != other.parts

    def __ge__(self, other: 'Version'):
        return self.parts >= other.parts

    def __gt__(self, other: 'Version'):
        return self.parts > other.parts

    def __le__(self, other: 'Version'):
        return self.parts <= other.parts

    def __lt__(self, other: 'Version'):
        return self.parts < other.parts
