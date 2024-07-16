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

import shlex

import cattr
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paas_wl.bk_app.cnative.specs.crd import bk_app
from paasng.platform.declarative.constants import AppSpecVersion
from paasng.platform.declarative.deployment.resources import DeploymentDesc
from paasng.platform.declarative.serializers import validate_language
from paasng.platform.declarative.utils import get_quota_plan
from paasng.platform.engine.constants import ConfigVarEnvName
from paasng.utils.serializers import IntegerOrCharField, field_env_var_key
from paasng.utils.validators import PROC_TYPE_MAX_LENGTH, PROC_TYPE_PATTERN


class EnvVariableSLZ(serializers.Serializer):
    """Serializer for describing a application's env_variable"""

    key = field_env_var_key()
    value = serializers.CharField(help_text="环境变量值", allow_blank=True)
    environment_name = serializers.ChoiceField(
        choices=ConfigVarEnvName.get_choices(), default=ConfigVarEnvName.GLOBAL.value
    )
    description = serializers.CharField(
        allow_blank=True,
        allow_null=True,
        max_length=200,
        required=False,
        default="",
        help_text="变量描述，不超过 200 个字符",
    )


class SvcBkSaaSSLZ(serializers.Serializer):
    """Serializer for describing SaaS item in service discovery"""

    bk_app_code = serializers.CharField(help_text="蓝鲸 App Code")
    module_name = serializers.CharField(required=False, help_text="需要获取服务地址的模块名")

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
    command = serializers.ListField(help_text="命令", child=serializers.CharField())


class HTTPGetSLZ(serializers.Serializer):
    port = IntegerOrCharField(help_text="访问端口或者端口名称")
    host = serializers.CharField(help_text="主机名", required=False)
    path = serializers.CharField(help_text="访问路径", required=False)
    http_headers = serializers.ListField(
        help_text="HTTP 请求标头", required=False, child=HTTPHeaderSLZ(), source="httpHeaders"
    )
    scheme = serializers.CharField(help_text="连接主机的方案", required=False, default="HTTP")


class TCPSocketSLZ(serializers.Serializer):
    port = IntegerOrCharField(help_text="访问端口或者端口名称")
    host = serializers.CharField(help_text="主机名", required=False, allow_null=True)


class ProbeSLZ(serializers.Serializer):
    exec = ExecSLZ(help_text="命令行探活检测机制", required=False)
    http_get = HTTPGetSLZ(help_text="http 请求探活检测机制", required=False, source="httpGet")
    tcp_socket = TCPSocketSLZ(help_text="tcp 请求探活检测机制", required=False, source="tcpSocket")

    initial_delay_seconds = serializers.IntegerField(
        help_text="容器启动后等待时间", required=False, source="initialDelaySeconds"
    )
    timeout_seconds = serializers.IntegerField(help_text="探针执行超时时间", required=False, source="timeoutSeconds")
    period_seconds = serializers.IntegerField(help_text="探针执行间隔时间", required=False, source="periodSeconds")
    success_threshold = serializers.IntegerField(
        help_text="连续几次检测成功后，判定容器是健康的", required=False, source="successThreshold"
    )
    failure_threshold = serializers.IntegerField(
        help_text="连续几次检测失败后，判定容器是不健康", required=False, source="failureThreshold"
    )

    def validate(self, data):
        # 根据实际需求进行校验
        if not any([data.get("exec"), data.get("httpGet"), data.get("tcpSocket")]):
            raise serializers.ValidationError(_("至少需要指定一个有效的探活检测机制"))

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
        # 尽可能将字段转换成 BkAppSepc
        # processes -> BkAppProcess
        processes = []
        for proc_type, process in attrs["processes"].items():
            processes.append(
                {
                    "name": proc_type,
                    "replicas": process["replicas"] or 1,
                    "resQuotaPlan": get_quota_plan(process["plan"]) if process.get("plan") else None,
                    "command": None,
                    "args": shlex.split(process["command"]),
                    "probes": process.get("probes"),
                    # proc_command 用于向后兼容普通应用部署场景
                    # (shlex.split + shlex.join 难以保证正确性)
                    "proc_command": process["command"],
                }
            )
        # scripts -> BkAppHooks
        hooks = {}
        if pre_release_hook := attrs["scripts"].get("pre_release_hook"):
            # 镜像已保证 entrypoint 是 /runner/init
            hooks["preRelease"] = {"command": None, "args": shlex.split(pre_release_hook)}

        # env_variables -> BkAppConfiguration
        global_vars = []
        env_vars = []
        for env_var in attrs.get("env_variables", []):
            if env_var["environment_name"] == ConfigVarEnvName.GLOBAL:
                global_vars.append({"name": env_var["key"], "value": env_var["value"]})
            else:
                env_vars.append(
                    {"envName": env_var["environment_name"], "name": env_var["key"], "value": env_var["value"]}
                )

        # svc_discovery -> SvcDiscConfig
        svc_discovery = {}
        if _svc_discovery_value := attrs.get("svc_discovery"):
            svc_discovery["bkSaaS"] = [
                {"bkAppCode": item["bk_app_code"], "moduleName": item.get("module_name")}
                for item in _svc_discovery_value["bk_saas"]
            ]

        spec = bk_app.BkAppSpec(
            processes=processes,
            hooks=hooks,
            configuration={"env": global_vars},
            envOverlay={
                "envVariables": env_vars,
            },
            svcDiscovery=svc_discovery,
        )
        return cattr.structure(
            {
                "language": attrs["language"],
                "source_dir": attrs["source_dir"],
                "bk_monitor": attrs.get("bk_monitor", None),
                "spec_version": AppSpecVersion.VER_2,
                "spec": spec,
            },
            DeploymentDesc,
        )

    def validate_processes(self, processes):
        for proc_type in processes:
            if not PROC_TYPE_PATTERN.match(proc_type):
                raise ValidationError(
                    f"Invalid proc type: {proc_type}, must match pattern {PROC_TYPE_PATTERN.pattern}"
                )
            if len(proc_type) > PROC_TYPE_MAX_LENGTH:
                raise ValidationError(
                    f"Invalid proc type: {proc_type}, cannot be longer than {PROC_TYPE_MAX_LENGTH} characters"
                )

        # Formalize procfile data and return
        return {k.lower(): v for k, v in processes.items()}
