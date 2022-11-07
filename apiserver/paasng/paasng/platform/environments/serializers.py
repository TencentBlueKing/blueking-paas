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
from rest_framework import serializers

from paasng.platform.modules.serializers import MinimalModuleSLZ

from .constants import EnvRoleOperation
from .models import EnvRoleProtection


class EnvRoleProtectionSLZ(serializers.ModelSerializer):
    module = serializers.SerializerMethodField()
    environment = serializers.SerializerMethodField()

    def get_environment(self, obj):
        return obj.module_env.environment

    def get_module(self, obj):
        return MinimalModuleSLZ(obj.module_env.module).data

    class Meta:
        model = EnvRoleProtection
        fields = ('allowed_role', 'operation', 'module', 'environment')


class EnvRoleProtectionListSLZ(serializers.Serializer):
    operation = serializers.ChoiceField(choices=EnvRoleOperation.get_choices())
    env = serializers.CharField(required=False)
    allowed_roles = serializers.ListField(child=serializers.IntegerField(), required=False)


class EnvRoleProtectionCreateSLZ(EnvRoleProtectionListSLZ):
    env = serializers.ChoiceField(choices=['stag', 'prod'])
