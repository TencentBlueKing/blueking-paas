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
from typing import List, Optional

from paas_wl.infras.cluster.shim import EnvClusterService, RegionClusterService
from paas_wl.infras.cluster.utils import get_cluster_by_app
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.mgrlegacy.entities import ClusterLegacyData, DefaultAppLegacyData
from paasng.platform.mgrlegacy.exceptions import PreCheckMigrationFailed

from .base import CNativeBaseMigrator


class BoundClusterMigrator(CNativeBaseMigrator):
    """BoundClusterMigrator to migrate the relationship between clusters and app(module)"""

    def _generate_legacy_data(self) -> Optional[DefaultAppLegacyData]:
        legacy_data: DefaultAppLegacyData = self.migration_process.legacy_data
        legacy_data.clusters = []

        for m in self.app.modules.all():
            for env in self._environments:
                wl_app = self._get_wl_app(m.name, env)
                legacy_data.clusters.append(
                    ClusterLegacyData(
                        module_name=m.name,
                        environment=env,
                        cluster_name=get_cluster_by_app(wl_app).name,
                    )
                )

        return legacy_data

    def _can_migrate(self):
        if self.app.type != ApplicationType.CLOUD_NATIVE.value:
            raise PreCheckMigrationFailed(
                "ApplicationTypeMigrator.migrate must be called before BoundClusterMigrator.migrate"
            )

    def _migrate(self):
        cnative_cluster = RegionClusterService(self.app.region).get_cnative_app_default_cluster()
        for env in self.app.get_app_envs():
            EnvClusterService(env).bind_cluster(cnative_cluster.name)

    def _rollback(self):
        clusters: List[ClusterLegacyData] = self.migration_process.legacy_data.clusters
        cluster_map = {(c.module_name, c.environment): c.cluster_name for c in clusters}

        for env in self.app.get_app_envs():
            EnvClusterService(env).bind_cluster(cluster_map[(env.module.name, env.environment)])
