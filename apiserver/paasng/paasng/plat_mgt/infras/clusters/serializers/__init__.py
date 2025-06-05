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

from .bcs_resources import (
    BCSClusterListOutputSLZ,
    BCSClusterServerUrlTmplRetrieveOutputSLZ,
    BCSProjectListOutputSLZ,
)
from .clusters import (
    ClusterCreateInputSLZ,
    ClusterListOutputSLZ,
    ClusterNodesStateRetrieveOutputSLZ,
    ClusterNodesStateSyncRecordListOutputSLZ,
    ClusterRetrieveOutputSLZ,
    ClusterStatusRetrieveOutputSLZ,
    ClusterUpdateInputSLZ,
    ClusterUsageRetrieveOutputSLZ,
)
from .components import (
    ClusterComponentListOutputSLZ,
    ClusterComponentRetrieveOutputSLZ,
    ClusterComponentUpsertInputSLZ,
)
from .default_configs import ClusterDefaultConfigListOutputSLZ
from .feature_flags import ClusterFeatureFlagListOutputSLZ
from .policies import (
    ClusterAllocationPolicyCondTypeOutputSLZ,
    ClusterAllocationPolicyCreateInputSLZ,
    ClusterAllocationPolicyCreateOutputSLZ,
    ClusterAllocationPolicyListOutputSLZ,
    ClusterAllocationPolicyUpdateInputSLZ,
)

__all__ = [
    # clusters
    "ClusterListOutputSLZ",
    "ClusterRetrieveOutputSLZ",
    "ClusterCreateInputSLZ",
    "ClusterUpdateInputSLZ",
    "ClusterStatusRetrieveOutputSLZ",
    "ClusterUsageRetrieveOutputSLZ",
    "ClusterNodesStateRetrieveOutputSLZ",
    "ClusterNodesStateSyncRecordListOutputSLZ",
    # components
    "ClusterComponentListOutputSLZ",
    "ClusterComponentRetrieveOutputSLZ",
    "ClusterComponentUpsertInputSLZ",
    # default_configs
    "ClusterDefaultConfigListOutputSLZ",
    # feature_flags
    "ClusterFeatureFlagListOutputSLZ",
    # policies
    "ClusterAllocationPolicyListOutputSLZ",
    "ClusterAllocationPolicyCreateInputSLZ",
    "ClusterAllocationPolicyCreateOutputSLZ",
    "ClusterAllocationPolicyUpdateInputSLZ",
    "ClusterAllocationPolicyCondTypeOutputSLZ",
    # bcs_resources
    "BCSClusterListOutputSLZ",
    "BCSProjectListOutputSLZ",
    "BCSClusterServerUrlTmplRetrieveOutputSLZ",
]
