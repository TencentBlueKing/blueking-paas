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
from typing import TYPE_CHECKING, Dict, List, Optional

from pydantic import BaseModel, Field

from paasng.platform.applications.constants import ApplicationType
from paasng.utils.structure import register

if TYPE_CHECKING:
    from paasng.platform.modules.constants import SourceOrigin


@register
class ClusterLegacyData(BaseModel):
    """Cluster info before migration"""

    module_name: str
    environment: str
    cluster_name: str


@register
class BuildLegacyData(BaseModel):
    """Build config info before migration"""

    module_name: str

    source_origin: "SourceOrigin"
    source_repo_id: Optional[int] = None
    source_type: Optional[str] = None

    buildpack_ids: Optional[List[int]] = None
    buildpack_builder_id: Optional[int] = None
    buildpack_runner_id: Optional[int] = None


@register
class DefaultAppLegacyData(BaseModel):
    """Data before migration, used for rollback"""

    app_type: str = ApplicationType.DEFAULT.value
    clusters: List[ClusterLegacyData] = Field(default_factory=list)
    builds: List[BuildLegacyData] = Field(default_factory=list)
    entrances: List[Dict] = Field(default_factory=list)


@register
class MigrationResult(BaseModel):
    """
    Record the result when the migrator performs a migration or rollback

    :param migrator_name: the name of migrator class
    :param is_succeeded: represents whether migrate or rollback is succeeded
    :param rollback_if_failed: represents whether rollback when the entire migration process failed. default is True
    :param error_msg: the error message when migrate or rollback
    """

    migrator_name: str
    is_succeeded: bool
    rollback_if_failed: bool = True
    error_msg: str = ""


RollbackResult = MigrationResult


@register
class ProcessDetails(BaseModel):
    """Details of migration or rollback process"""

    migrations: List[MigrationResult] = Field(default_factory=list)
    rollbacks: List[RollbackResult] = Field(default_factory=list)
