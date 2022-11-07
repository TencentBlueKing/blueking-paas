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

from paasng.engine.models import EngineApp
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.modules.models import Module


class AppInstSLZ(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ['id', 'type', 'region', 'code', 'name']


class ModuleInstSLZ(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ['id', 'name']


class ModuleEnvInstSLZ(serializers.ModelSerializer):
    engine_app_id = serializers.CharField(read_only=True)

    class Meta:
        model = ModuleEnvironment
        fields = ['id', 'environment', 'engine_app_id', 'is_offlined']


class EngineAppInstSLZ(serializers.ModelSerializer):
    class Meta:
        model = EngineApp
        fields = ['id', 'name']


class AppInstanceInfoSLZ(serializers.Serializer):
    """Serialize an application instance, may include module and module_env objects"""

    application = AppInstSLZ()
    module = ModuleInstSLZ(required=False)
    module_env = ModuleEnvInstSLZ(required=False)
    engine_app = EngineAppInstSLZ(required=False)
