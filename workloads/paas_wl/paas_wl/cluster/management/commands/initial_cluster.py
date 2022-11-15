"""
Tencent is pleased to support the open source community by making BlueKing - PaaS System available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
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
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

import jinja2
from django.conf import settings
from django.core.management.base import BaseCommand

from paas_wl.cluster.constants import ClusterTokenType
from paas_wl.cluster.models import APIServer, Cluster

logger = logging.getLogger(__name__)


@dataclass
class ClusterData:
    region: str
    name: str
    is_default: bool = False
    description: Optional[str] = None
    ingress_config: Optional[Dict] = None
    annotations: Optional[Dict] = None
    ca_data: Optional[str] = None
    cert_data: Optional[str] = None
    key_data: Optional[str] = None
    token_type: Optional[ClusterTokenType] = None
    token_value: Optional[str] = None
    default_node_selector: Optional[Dict] = None
    default_tolerations: Optional[List] = None


@dataclass
class InitialClusterData:
    cluster_id: str
    cluster_data: ClusterData
    api_server_urls: list


class Command(BaseCommand):
    help = "Initialize the application cluster, which can overwrite the existing data in the database"

    def add_arguments(self, parser):
        parser.add_argument('--override', dest="override", action='store_true')
        parser.add_argument('--dry_run', dest="dry_run", action='store_true')

    def render_data(self) -> InitialClusterData:
        cluster_data_path = Path(settings.BASE_DIR) / 'support-files' / 'initial_data' / 'cluster.json.j2'

        # 初始化集群的配置信息通过环境变量渲染
        data_str = jinja2.Template(cluster_data_path.read_text()).render(os.environ)
        try:
            data = json.loads(data_str)
        except Exception as e:
            raise ValueError(f"{cluster_data_path} is not a valid json") from e
        if not isinstance(data, dict):
            raise ValueError(f"{cluster_data_path} is not a valid dict")
        if "pk" not in data:
            raise ValueError(f"{cluster_data_path} does not contain a pk field, cannot be initialized")

        cluster_id = data['pk']
        cluster_data = ClusterData(**data['fields'])
        # 容忍度和污点是用户填写的结构化数据，直接从环境变量中获取,需要转换为 json 格式
        node_selector = os.environ.get('PAAS_WL_CLUSTER_NODE_SELECTOR', "{}")
        toleration = os.environ.get('PAAS_WL_CLUSTER_TOLERATIONS', "[]")
        try:
            cluster_data.default_node_selector = json.loads(node_selector)
            cluster_data.default_tolerations = json.loads(toleration)
        except Exception as e:
            logger.error(f"node_selector: {node_selector}\ntoleration: {toleration} \nare not valid json")
            raise ValueError("node_selector and toleration are not valid json") from e

        api_server_urls = os.environ.get('PAAS_WL_CLUSTER_API_SERVER_URLS')
        api_server_list = api_server_urls.split(";") if api_server_urls else []

        return InitialClusterData(cluster_id=cluster_id, cluster_data=cluster_data, api_server_urls=api_server_list)

    def handle(self, override, dry_run, *args, **options):
        data = self.render_data()

        cluster_qs = Cluster.objects.filter(pk=data.cluster_id)

        if cluster_qs.exists() and not override:
            logger.info("The cluster(pk:%s) already exists and overwriting is not allowed, skip", data.cluster_id)
            return

        if dry_run:
            logger.info("DRY-RUN: preparing to initialize the cluster, data: %s", data)
            return

        cluster = Cluster.objects.register_cluster(pk=data.cluster_id, **asdict(data.cluster_data))

        for _url in data.api_server_urls:
            APIServer.objects.get_or_create(cluster=cluster, host=_url)
        APIServer.objects.exclude(host__in=data.api_server_urls).delete()
        logger.info("The cluster was initialized successfully")
