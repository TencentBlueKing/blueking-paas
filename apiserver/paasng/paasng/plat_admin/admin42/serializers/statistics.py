# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from datetime import datetime, timedelta

from rest_framework import serializers


class AppDeploymentFilterSlz(serializers.Serializer):
    start_time = serializers.DateTimeField(required=False)
    end_time = serializers.DateTimeField(required=False)
    only_prod = serializers.BooleanField(required=False)

    def validate(self, data):
        # 开始时间默认为 1 年前
        if 'start_time' not in data:
            data['start_time'] = datetime.now() - timedelta(days=365)

        if 'end_time' not in data:
            data['end_time'] = datetime.now()

        return data


class AppDeploymentSlz(serializers.Serializer):
    name = serializers.CharField(help_text="应用名称")
    code = serializers.CharField(help_text="应用ID")
    last_operator = serializers.CharField(help_text="最近操作人")
    total = serializers.IntegerField(help_text="总的部署次数")
    monthly_summary = serializers.CharField(help_text="每月部署次数汇总")


class DeveloperDeploymentSlz(serializers.Serializer):
    developer = serializers.CharField(help_text="开发者")
    total = serializers.IntegerField(help_text="总的部署次数")
    monthly_summary = serializers.CharField(help_text="每月部署次数汇总")
