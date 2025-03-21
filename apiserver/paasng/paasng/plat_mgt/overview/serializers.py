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

from rest_framework import serializers


class ClusterConfigStatusSLZ(serializers.Serializer):
    """集群配置状态"""

    allocated = serializers.BooleanField(help_text="是否已分配")


class AddonsServiceConfigStatusSLZ(serializers.Serializer):
    """增强服务配置状态"""

    id = serializers.CharField(help_text="ID")
    name = serializers.CharField(help_text="名称")
    bind = serializers.BooleanField(help_text="是否已绑定")


class TenantConfigStatusOutputSLZ(serializers.Serializer):
    """租户配置状态"""

    tenant_id = serializers.CharField(help_text="租户 ID")
    tenant_name = serializers.CharField(help_text="租户名称")
    cluster = ClusterConfigStatusSLZ(help_text="集群配置状态")
    addons_service = serializers.ListField(help_text="增强服务配置状态", child=AddonsServiceConfigStatusSLZ())
