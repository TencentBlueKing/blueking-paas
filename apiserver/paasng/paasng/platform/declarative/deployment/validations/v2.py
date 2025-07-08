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
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paasng.platform.applications.serializers.fields import SourceDirField
from paasng.platform.bkapp_model.entities import v1alpha2
from paasng.platform.bkapp_model.serializers import ProbeSetSLZ, SvcDiscConfigSLZ
from paasng.platform.declarative.constants import AppSpecVersion
from paasng.platform.declarative.deployment.resources import DeploymentDesc
from paasng.platform.declarative.serializers import validate_language
from paasng.platform.declarative.utils import get_quota_plan
from paasng.platform.engine.constants import ConfigVarEnvName
from paasng.utils.serializers import field_env_var_key
from paasng.utils.structure import NOTSET, NotSetType
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


class ProcessSLZ(serializers.Serializer):
    command = serializers.CharField(help_text="进程启动指令")
    replicas = serializers.IntegerField(default=NOTSET, help_text="进程副本数", allow_null=True)
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
    source_dir = SourceDirField(help_text="源码目录")
    env_variables = serializers.ListField(child=EnvVariableSLZ(), required=False)
    processes = serializers.DictField(
        help_text="key: 进程名称, value: 进程信息", default=dict, child=ProcessSLZ(), allow_empty=False
    )
    svc_discovery = SvcDiscConfigSLZ(help_text="应用所需服务发现配置", default=NOTSET)
    scripts = serializers.DictField(help_text="key: 脚本名称, value: 脚本指令内容", default=NOTSET)
    bkmonitor = BluekingMonitorSLZ(help_text="SaaS 监控采集配置", required=False, source="bk_monitor")

    def to_internal_value(self, data) -> DeploymentDesc:
        attrs = super().to_internal_value(data)
        # 尽可能将字段转换成 BkAppSpec 对象
        # processes -> BkAppProcess
        processes = []
        for proc_type, process in attrs["processes"].items():
            processes.append(
                {
                    "name": proc_type,
                    # NOTE: 此处的 replicas 可能为 None，也被允许使用 None
                    "replicas": process["replicas"],
                    "res_quota_plan": get_quota_plan(process["plan"]) if process.get("plan") else None,
                    # proc_command 用于向后兼容普通应用部署场景
                    # (shlex.split + shlex.join 难以保证正确性)
                    "proc_command": process["command"],
                    "command": None,
                    "args": shlex.split(process["command"]),
                    "probes": process.get("probes"),
                }
            )
        # scripts -> BkAppHooks
        hooks: NotSetType | dict = NOTSET
        if attrs["scripts"] and (pre_release_hook := attrs["scripts"].get("pre_release_hook")):
            # 镜像已保证 entrypoint 是 /runner/init
            hooks = {"pre_release": {"command": [], "args": shlex.split(pre_release_hook)}}

        # env_variables -> BkAppConfiguration
        global_vars = []
        env_vars = []
        for env_var in attrs.get("env_variables", []):
            if env_var["environment_name"] == ConfigVarEnvName.GLOBAL:
                global_vars.append({"name": env_var["key"], "value": env_var["value"]})
            else:
                env_vars.append(
                    {"env_name": env_var["environment_name"], "name": env_var["key"], "value": env_var["value"]}
                )

        # The only possible member of the `env_overlay` field is `env_variables`, if
        # there are no env vars then the field should be set to NOTSET.
        env_overlay: NotSetType | dict
        if not env_vars:
            env_overlay = NOTSET
        else:
            env_overlay = {"env_variables": env_vars}

        # svc_discovery -> SvcDiscConfig
        _svc_discovery_value = attrs.get("svc_discovery")
        svc_discovery: NotSetType | dict[str, list[dict]]
        if _svc_discovery_value == NOTSET:
            svc_discovery = NOTSET
        else:
            svc_discovery = {}
            if bk_sass := _svc_discovery_value.get("bk_saas"):
                svc_discovery["bk_saas"] = [
                    {"bk_app_code": item["bk_app_code"], "module_name": item.get("module_name")} for item in bk_sass
                ]

        spec = v1alpha2.BkAppSpec(
            processes=processes,
            hooks=hooks,
            configuration={"env": global_vars},
            env_overlay=env_overlay,
            svc_discovery=svc_discovery,
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
