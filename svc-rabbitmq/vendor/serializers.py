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


class PlanConfigSerializer(serializers.Serializer):
    host = serializers.CharField(required=True)
    port = serializers.IntegerField(default=5672)
    api_port = serializers.IntegerField(default=15672)
    api_url = serializers.CharField(required=False, allow_null=True, default=None)
    admin = serializers.CharField(default="admin")
    password = serializers.CharField(required=True)
    cluster_version = serializers.CharField(default="3.7.8")
    management_api = serializers.SerializerMethodField(help_text="管理接口")

    def get_management_api(self, obj):
        api_url = obj.get("api_url")
        if obj.get("api_url") is not None:
            return api_url
        else:
            host = obj.get("host")
            api_port = obj.get("api_port")

            return f"http://{host}:{api_port}"
