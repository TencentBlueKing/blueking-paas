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

from typing import List, Optional

from paas_wl.infras.cluster.shim import EnvClusterService
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.mgrlegacy.entities import ClusterLegacyData, DefaultAppLegacyData
from paasng.platform.mgrlegacy.exceptions import PreCheckMigrationFailed
from paasng.platform.mgrlegacy.utils import get_cnative_target_cluster

from .base import CNativeBaseMigrator


class ApplicationClusterMigrator(CNativeBaseMigrator):
    """ApplicationClusterMigrator to migrate the relationship between clusters and app(module)"""

    def _generate_legacy_data(self) -> Optional[DefaultAppLegacyData]:
        legacy_data: DefaultAppLegacyData = self.migration_process.legacy_data
        legacy_data.clusters = []

        for m in self.app.modules.all():
            for env in m.envs.all():
                if cluster_name := env.wl_app.config_set.latest().cluster:
                    legacy_data.clusters.append(
                        ClusterLegacyData(module_name=m.name, environment=env.environment, cluster_name=cluster_name)
                    )
                else:
                    raise PreCheckMigrationFailed(f"no valid cluster bound with module({m.name})")

        return legacy_data

    def _can_migrate_or_raise(self):
        if self.app.type != ApplicationType.CLOUD_NATIVE.value:
            raise PreCheckMigrationFailed(f"app({self.app.code}) type does not set to cloud_native")

    def _migrate(self):
        cnative_cluster_name = get_cnative_target_cluster().name
        for env in self.app.get_app_envs():
            EnvClusterService(env).bind_cluster(cnative_cluster_name)

    def _rollback(self):
        clusters: List[ClusterLegacyData] = self.migration_process.legacy_data.clusters
        cluster_map = {(c.module_name, c.environment): c.cluster_name for c in clusters}

        for env in self.app.get_app_envs():
            EnvClusterService(env).bind_cluster(cluster_map[(env.module.name, env.environment)])
