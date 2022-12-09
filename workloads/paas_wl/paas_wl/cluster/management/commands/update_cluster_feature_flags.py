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
import logging

from django.core.management.base import BaseCommand

from paas_wl.cluster.constants import ClusterFeatureFlag, ClusterType
from paas_wl.cluster.models import Cluster

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "update cluster feature flags"

    def add_arguments(self, parser):
        parser.add_argument('--cluster-names', nargs='*', help='specified cluster name list')

    def handle(self, cluster_names, *args, **options):
        cluster_qs = Cluster.objects.all()
        if cluster_names:
            cluster_qs = cluster_qs.objects.filter(name__in=cluster_names)

        for cluster in cluster_qs:
            # 根据集群类型更新 feature flag
            if cluster.type == ClusterType.NORMAL:
                cluster.feature_flags.update(
                    {
                        ClusterFeatureFlag.ENABLE_EGRESS_IP: True,
                        ClusterFeatureFlag.ENABLE_MOUNT_LOG_TO_HOST: True,
                    }
                )
            elif cluster.type == ClusterType.VIRTUAL:
                cluster.feature_flags.update(
                    {
                        ClusterFeatureFlag.ENABLE_EGRESS_IP: False,
                        ClusterFeatureFlag.ENABLE_MOUNT_LOG_TO_HOST: False,
                    }
                )

            print(f"update cluster {cluster.name}'s feature flags... done")
            cluster.save()
