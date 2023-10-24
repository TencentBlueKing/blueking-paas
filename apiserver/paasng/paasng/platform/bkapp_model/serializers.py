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
from django.conf import settings
from rest_framework import serializers

from paas_wl.bk_app.cnative.specs.constants import ScalingPolicy
from paas_wl.bk_app.processes.drf_serializers import MetricSpecSLZ
from paasng.platform.modules.constants import DeployHookType

DEFAULT_METRICS = [
    {
        "type": 'Resource',
        "metric": 'cpuUtilization',
        "value": '85%',
    },
]


def default_scaling_config():
    return {"min_replicas": 1, "max_replicas": 1, "metrics": DEFAULT_METRICS, "policy": ScalingPolicy.DEFAULT}


class GetManifestInputSLZ(serializers.Serializer):
    output_format = serializers.ChoiceField(
        help_text='The output format', choices=['json', 'yaml'], required=False, default='json'
    )


class ScalingConfigSLZ(serializers.Serializer):
    """扩缩容配置"""

    min_replicas = serializers.IntegerField(required=True, min_value=1, help_text="最小副本数")
    max_replicas = serializers.IntegerField(required=True, min_value=1, help_text="最大副本数")
    metrics = serializers.ListField(
        child=MetricSpecSLZ(), min_length=1, help_text="扩缩容指标", default=lambda: DEFAULT_METRICS
    )
    policy = serializers.CharField(help_text="扩缩容策略", default=ScalingPolicy.DEFAULT)


class ProcessSpecEnvOverlaySLZ(serializers.Serializer):
    """进程配置-环境相关配置"""

    environment_name = serializers.CharField(help_text="环境名称")

    plan_name = serializers.CharField(help_text="资源配额方案", required=False)
    target_replicas = serializers.IntegerField(help_text="副本数量(手动调节)", min_value=0, required=False)
    autoscaling = serializers.BooleanField(help_text="是否启用自动扩缩容", required=False, default=False)
    scaling_config = ScalingConfigSLZ(help_text="自动扩缩容配置", required=False, default=default_scaling_config)


class ModuleProcessSpecMetadataSLZ(serializers.Serializer):
    """特性开关"""

    allow_set_image = serializers.BooleanField(default=False, help_text="是否允许编辑 image 字段")


class ModuleProcessSpecSLZ(serializers.Serializer):
    """进程配置"""

    name = serializers.CharField(help_text="进程名称")

    image = serializers.CharField(help_text="镜像仓库/镜像地址", allow_null=True, required=False)
    image_credential_name = serializers.CharField(help_text="镜像凭证", allow_null=True, required=False)
    command = serializers.ListSerializer(child=serializers.CharField(), help_text="启动命令", default=list)
    args = serializers.ListSerializer(child=serializers.CharField(), help_text="命令参数", default=list)
    port = serializers.IntegerField(help_text="容器端口", min_value=1, max_value=65535, default=settings.CONTAINER_PORT)
    env_overlay = serializers.DictField(child=ProcessSpecEnvOverlaySLZ(), help_text="环境相关配置", required=False)


class ModuleProcessSpecsOutputSLZ(serializers.Serializer):
    proc_specs = ModuleProcessSpecSLZ(many=True, read_only=True)
    metadata = ModuleProcessSpecMetadataSLZ(read_only=True)


class ModuleDeployHookSLZ(serializers.Serializer):
    """钩子命令"""

    type = serializers.ChoiceField(help_text="钩子类型", choices=DeployHookType.get_choices())

    proc_command = serializers.CharField(
        help_text="进程启动命令(包含完整命令和参数的字符串), 只能与 command/args 二选一", required=False, allow_null=True
    )
    command = serializers.ListSerializer(child=serializers.CharField(), help_text="启动命令", default=list)
    args = serializers.ListSerializer(child=serializers.CharField(), help_text="命令参数", default=list)
    enabled = serializers.BooleanField(allow_null=True, default=False)
