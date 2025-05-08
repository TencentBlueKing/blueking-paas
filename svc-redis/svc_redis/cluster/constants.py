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


from blue_krill.data_types.enum import EnumField, IntStructuredEnum, StrStructuredEnum
from django.utils.translation import gettext_lazy as _


class ClusterTokenType(IntStructuredEnum):
    SERVICE_ACCOUNT = 1


class ClusterType(StrStructuredEnum):
    """集群类别"""

    NORMAL = EnumField("normal", label=_("普通集群"))
    VIRTUAL = EnumField("virtual", label=_("虚拟集群"))


class ClusterAnnotationKey(StrStructuredEnum):
    """集群注解键"""

    BCS_PROJECT_ID = EnumField("bcs_project_id", label=_("BCS 项目 ID"))
    BCS_CLUSTER_ID = EnumField("bcs_cluster_id", label=_("BCS 集群 ID"))
    BK_BIZ_ID = EnumField("bk_biz_id", label=_("蓝鲸业务 ID"))
