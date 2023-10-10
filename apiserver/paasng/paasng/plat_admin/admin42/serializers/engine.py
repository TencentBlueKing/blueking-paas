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
from typing import Optional

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from paas_wl.infras.cluster.shim import EnvClusterService
from paasng.platform.engine.constants import JobStatus
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.engine.models.operations import ModuleEnvironmentOperations
from paasng.platform.engine.serializers import OperationSLZ as BaseModuleEnvironmentOperationsSLZ
from paasng.platform.applications.models import ModuleEnvironment
from paasng.utils.serializers import HumanizeDateTimeField, UserNameField


class ModuleEnvironmentOperationsSLZ(BaseModuleEnvironmentOperationsSLZ):
    operator = UserNameField()
    created_humanized = HumanizeDateTimeField(source="created")

    class Meta:
        model = ModuleEnvironmentOperations
        fields = [
            'id',
            'status',
            'operator',
            'created',
            'operation_type',
            'offline_operation',
            'deployment',
            'created_humanized',
        ]


class EnvironmentSLZ(serializers.ModelSerializer):
    latest_operation = serializers.SerializerMethodField()
    latest_successful_operation = serializers.SerializerMethodField()
    cluster_name = serializers.SerializerMethodField()

    @staticmethod
    def get_latest_operation(obj: ModuleEnvironment):
        try:
            return ModuleEnvironmentOperationsSLZ(obj.module_operations.latest("created")).data
        except ModuleEnvironmentOperations.DoesNotExist:
            return None

    @staticmethod
    def get_latest_successful_operation(obj: ModuleEnvironment):
        try:
            return ModuleEnvironmentOperationsSLZ(
                obj.module_operations.filter(status=JobStatus.SUCCESSFUL.value).latest("created")
            ).data
        except ModuleEnvironmentOperations.DoesNotExist:
            return None

    @staticmethod
    def get_cluster_name(env: ModuleEnvironment) -> Optional[str]:
        try:
            return EnvClusterService(env).get_cluster_name()
        except ObjectDoesNotExist:
            return None

    class Meta:
        model = ModuleEnvironment
        fields = '__all__'


class DeploymentForListSLZ(serializers.ModelSerializer):
    f_application_id = serializers.CharField(read_only=True)
    f_application_name = serializers.CharField(read_only=True)
    f_module_name = serializers.CharField(read_only=True)
    f_environment = serializers.CharField(read_only=True)

    class Meta:
        model = Deployment
        exclude = ('procfile', 'processes', 'hooks')
