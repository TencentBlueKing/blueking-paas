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


class BCSProjectListOutputSLZ(serializers.Serializer):
    """BCS 项目信息"""

    id = serializers.CharField(help_text="项目 ID", source="projectID")
    code = serializers.CharField(help_text="项目 Code", source="projectCode")
    name = serializers.CharField(help_text="项目名称")
    description = serializers.CharField(help_text="项目描述")
    biz_id = serializers.CharField(help_text="业务 ID", source="businessID")
    biz_name = serializers.CharField(help_text="业务名称", source="businessName")


class BCSClusterListOutputSLZ(serializers.Serializer):
    """BCS 集群信息"""

    id = serializers.CharField(help_text="集群 ID", source="clusterID")
    name = serializers.CharField(help_text="集群名称", source="clusterName")
    environment = serializers.CharField(help_text="集群环境")


class BCSClusterServerUrlTmplRetrieveOutputSLZ(serializers.Serializer):
    url_tmpl = serializers.CharField(help_text="集群 Server URL 模板")
