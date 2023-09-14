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
import cattr
from rest_framework import serializers

from paasng.engine.constants import ConfigVarEnvName
from paasng.extensions.declarative.deployment.resources import DeploymentDesc
from paasng.extensions.declarative.serializers import validate_language
from paasng.utils.serializers import field_env_var_key


class EnvVariableSLZ(serializers.Serializer):
    """Serializer for describing a application's env_variable"""

    key = field_env_var_key()
    value = serializers.CharField(help_text="环境变量值", allow_blank=True)
    environment_name = serializers.ChoiceField(
        choices=ConfigVarEnvName.get_choices(), default=ConfigVarEnvName.GLOBAL.value
    )
    description = serializers.CharField(
        allow_blank=True, allow_null=True, max_length=200, required=False, default='', help_text='变量描述，不超过 200 个字符'
    )


class SvcBkSaaSSLZ(serializers.Serializer):
    """Serializer for describing SaaS item in service discovery"""

    bk_app_code = serializers.CharField(help_text='蓝鲸 App Code')
    module_name = serializers.CharField(required=False, help_text='需要获取服务地址的模块名')

    def to_internal_value(self, data):
        # Note: 兼容只传递 app-code 的格式
        if isinstance(data, str):
            data = {"bk_app_code": data}
        return super().to_internal_value(data)


class SvcDiscoverySLZ(serializers.Serializer):
    """Serializer for describing service discovery"""

    bk_saas = serializers.ListField(child=SvcBkSaaSSLZ())


class HTTPHeaderSLZ(serializers.Serializer):
    name = serializers.CharField(help_text="标头名称")
    value = serializers.CharField(help_text="标头值")


class ExecSLZ(serializers.Serializer):
    command = serializers.ListField(help_text="访问路径", child=serializers.CharField())


class HTTPGetSLZ(serializers.Serializer):
    port = serializers.CharField(help_text="访问端口或者端口名称")
    host = serializers.CharField(help_text="主机名", required=False)
    path = serializers.CharField(help_text="访问路径", required=False)
    http_headers = serializers.ListField(help_text="HTTP 请求标头", required=False, child=HTTPHeaderSLZ())
    scheme = serializers.CharField(help_text="连接主机的方案", required=False)


class TCPSocketSLZ(serializers.Serializer):
    port = serializers.CharField(help_text="访问端口或者端口名称")
    host = serializers.CharField(help_text="主机名", required=False, allow_null=True)


class ProbeSLZ(serializers.Serializer):
    exec = ExecSLZ(help_text="命令行探活检测机制", required=False)
    http_get = HTTPGetSLZ(help_text="http 请求探活检测机制", required=False)
    tcp_socket = TCPSocketSLZ(help_text="tcp 请求探活检测机制", required=False)

    initial_delay_seconds = serializers.IntegerField(help_text="容器启动后等待时间", required=False)
    timeout_seconds = serializers.IntegerField(help_text="探针执行超时时间", required=False)
    period_seconds = serializers.IntegerField(help_text="探针执行间隔时间", required=False)
    success_threshold = serializers.IntegerField(help_text="连续几次检测成功后，判定容器是健康的", required=False)
    failure_threshold = serializers.IntegerField(help_text="连续几次检测失败后，判定容器是不健康", required=False)

    def validate(self, data):
        # 根据实际需求进行校验
        if not any([data.get('exec'), data.get('http_get'), data.get('tcp_socket')]):
            raise serializers.ValidationError("至少需要指定一个有效的探活检测机制")

        return super().validate(data)


class ProbeSetSLZ(serializers.Serializer):
    liveness = ProbeSLZ(default=None, help_text="存活探针", required=False)
    readiness = ProbeSLZ(default=None, help_text="就绪探针", required=False)
    startup = ProbeSLZ(default=None, help_text="启动探针", required=False)


class ProcessSLZ(serializers.Serializer):
    command = serializers.CharField(help_text="进程启动指令")
    replicas = serializers.IntegerField(default=None, help_text="进程副本数", allow_null=True)
    plan = serializers.CharField(help_text="资源方案名称", required=False, allow_blank=True, allow_null=True)
    probes = ProbeSetSLZ(default=None, help_text="探针集合", required=False)


class BluekingMonitorSLZ(serializers.Serializer):
    port = serializers.IntegerField(help_text="Service 暴露的端口号")
    target_port = serializers.IntegerField(
        required=False, allow_null=False, help_text="Service 关联的容器内的端口号, 不设置则使用 port"
    )


class DeploymentDescSLZ(serializers.Serializer):
    """Serializer for describing application's deployment part."""

    language = serializers.CharField(help_text="模块开发语言", validators=[validate_language])
    source_dir = serializers.CharField(help_text="源码目录", default="")
    env_variables = serializers.ListField(child=EnvVariableSLZ(), required=False)
    processes = serializers.DictField(help_text="key: 进程名称, value: 进程信息", default=dict, child=ProcessSLZ())
    svc_discovery = SvcDiscoverySLZ(help_text="应用所需服务发现配置", required=False)
    scripts = serializers.DictField(help_text="key: 脚本名称, value: 脚本指令内容", default=dict)
    bkmonitor = BluekingMonitorSLZ(help_text="SaaS 监控采集配置", required=False, source="bk_monitor")

    def to_internal_value(self, data) -> DeploymentDesc:
        attrs = super().to_internal_value(data)
        return cattr.structure(attrs, DeploymentDesc)
