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

import copy
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import UUID

import arrow
import cattr
from dateutil import parser
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from kubernetes.utils.quantity import parse_quantity
from rest_framework import serializers
from rest_framework.serializers import ValidationError

from paas_wl.bk_app.applications.models import Release
from paas_wl.bk_app.processes.constants import ProcessUpdateType
from paas_wl.bk_app.processes.kres_entities import Instance, Process
from paas_wl.bk_app.processes.models import ProcessSpec
from paas_wl.infras.resources.kube_res.base import WatchEvent
from paas_wl.workloads.autoscaling.constants import ScalingMetric, ScalingMetricSourceType
from paas_wl.workloads.autoscaling.entities import AutoscalingConfig
from paas_wl.workloads.networking.ingress.utils import get_service_dns_name
from paasng.platform.engine.constants import JobStatus, RuntimeType
from paasng.platform.engine.models import Deployment, OfflineOperation
from paasng.platform.sourcectl.models import VersionInfo


class HumanizeDateTimeField(serializers.DateTimeField):
    def to_representation(self, value):
        return arrow.get(value).humanize(locale="zh")


class ProcessForDisplaySLZ(serializers.Serializer):
    """Common serializer for representing Process object"""

    # Warning: 这个字段需要查询数据库
    module_name = serializers.CharField(source="app.module_name", help_text="模块名")

    name = serializers.CharField(source="metadata.name")
    type = serializers.CharField(help_text="进程类型(名称)")
    command = serializers.CharField(source="runtime.proc_command", help_text="进程命令")

    replicas = serializers.IntegerField(source="status.replicas", help_text="期望实例数")
    success = serializers.IntegerField(source="status.success", help_text="成功进程个数")
    failed = serializers.IntegerField(source="status.failed", help_text="失败进程个数")
    version = serializers.IntegerField(help_text="release version")

    cluster_link = serializers.SerializerMethodField()

    def get_cluster_link(self, process: Process) -> str:
        return f"http://{get_service_dns_name(process.app, process.type)}"


class InstanceForDisplaySLZ(serializers.Serializer):
    """Common serializer for representing Instance object, removes some extra
    large and sensitive fields such as "envs" """

    # Warning: 这个字段需要查询数据库
    module_name = serializers.CharField(source="app.module_name")

    name = serializers.CharField(read_only=True)
    process_type = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True, source="shorter_name")
    image = serializers.CharField(read_only=True)
    start_time = serializers.CharField(read_only=True)
    state = serializers.SerializerMethodField(read_only=True, help_text="实例状态")
    state_message = serializers.CharField(read_only=True)
    rich_status = serializers.CharField(read_only=True)
    ready = serializers.BooleanField(read_only=True)
    restart_count = serializers.IntegerField()
    terminated_info = serializers.DictField(read_only=True, help_text="终止信息")
    version = serializers.CharField(read_only=True)

    def get_state(self, obj: Instance) -> str:
        """Sometimes the target pod may enter into 'Running' phase without being ready,
        which may confuses users, translate those states into "Starting"
        """
        if not obj.ready and obj.state == "Running":
            # Not using word "Pending" because it's already an Kubernetes Pod state
            return "Starting"
        return obj.state


class ProcessExtraInfoSLZ(serializers.Serializer):
    """part of SLZ for ProcessInstanceListWatcher.list"""

    type = serializers.CharField(help_text="进程类型")
    command = serializers.CharField(help_text="进程命令")
    cluster_link = serializers.CharField(help_text="集群内访问地址")


class ListRespMetaDataSLZ(serializers.Serializer):
    """part of SLZ for ProcessInstanceListWatcher.list"""

    resource_version = serializers.CharField(help_text="k8s 资源版本")


class ProcessListSLZ(serializers.Serializer):
    """part of SLZ for ProcessInstanceListWatcher.list"""

    items = ProcessForDisplaySLZ(many=True)
    extra_infos = ProcessExtraInfoSLZ(
        many=True, required=False, help_text="[deprecated] 相关信息移动到 ProcessForDisplaySLZ"
    )
    metadata = ListRespMetaDataSLZ()


class InstanceListSLZ(serializers.Serializer):
    """part of SLZ for ProcessInstanceListWatcher.list"""

    items = InstanceForDisplaySLZ(many=True)
    metadata = ListRespMetaDataSLZ()


class EventSerializer(serializers.Serializer):
    reason = serializers.CharField(help_text="事件发生的原因", required=False, allow_null=True)
    count = serializers.IntegerField(help_text="事件发生的次数")
    type = serializers.CharField(help_text="事件的类型", required=False, allow_null=True)
    message = serializers.CharField(help_text="事件内容", required=False, allow_null=True)
    first_timestamp = serializers.CharField(required=False, allow_null=True)
    last_timestamp = serializers.CharField(required=False, allow_null=True)


class ListWatcherRespSLZ(serializers.Serializer):
    """SLZ for ProcessInstanceListWatcher.list"""

    processes = ProcessListSLZ()
    instances = InstanceListSLZ()
    cnative_proc_specs = serializers.ListField(required=False, child=serializers.DictField())
    process_packages = serializers.ListField(required=False, child=serializers.DictField())


class VersionInfoSLZ(serializers.Serializer):
    """已部署的代码/镜像版本信息"""

    revision = serializers.CharField(help_text="版本hash")
    version_name = serializers.CharField(help_text="版本名称")
    version_type = serializers.CharField(help_text="版本类型(tag/branch)")


class DeploymentOperationSLZ(serializers.Serializer):
    """部署操作对象"""

    id = serializers.CharField(help_text="部署ID")
    status = serializers.ChoiceField(choices=JobStatus.get_choices())
    created = serializers.DateTimeField(help_text="操作时间")

    version_info = VersionInfoSLZ(help_text="版本信息")
    err_detail = serializers.CharField(help_text="错误原因")
    has_requested_int = serializers.BooleanField(help_text="部署是否被中断")

    advanced_options = serializers.SerializerMethodField(allow_null=True)

    def get_advanced_options(self, obj: Deployment) -> Dict:
        if obj.advanced_options:
            return {
                "image_pull_policy": obj.advanced_options.image_pull_policy.value,
            }
        return {}


class OfflineOperationSLZ(serializers.Serializer):
    """下架操作对象"""

    id = serializers.CharField(help_text="下架ID")
    status = serializers.ChoiceField(choices=JobStatus.get_choices())
    created = serializers.DateTimeField(help_text="操作时间")


def make_operation_group_slz(child: serializers.Serializer):
    return type(
        f"{type(child).__name__}Group",
        (serializers.Serializer,),
        {
            "latest": copy.deepcopy(child),
            "latest_succeeded": copy.deepcopy(child),
            "pending": copy.deepcopy(child),
        },
    )()


class ModuleStateSLZ(serializers.Serializer):
    """和模块相关的部署/下架对象"""

    deployment = make_operation_group_slz(DeploymentOperationSLZ(help_text="部署操作对象", allow_null=True))
    offline = make_operation_group_slz(OfflineOperationSLZ(help_text="下架操作对象", allow_null=True))


class NamespaceScopedListWatchRespPartSLZ(serializers.Serializer):
    module_name = serializers.CharField()
    state = ModuleStateSLZ(help_text="模块状态")
    exposed_url = serializers.CharField(required=False, help_text="访问地址")
    repo_url = serializers.CharField(required=False, help_text="源码/镜像仓库地址")
    build_method = serializers.CharField(help_text="构建方式")
    version_info = VersionInfoSLZ(required=False)

    processes = ProcessForDisplaySLZ(many=True)
    instances = InstanceForDisplaySLZ(many=True)
    proc_specs = serializers.ListField(child=serializers.DictField())

    total_available_instance_count = serializers.IntegerField(help_text="总运行实例数")
    total_desired_replicas = serializers.IntegerField(help_text="总期望实例数")
    total_failed = serializers.IntegerField(help_text="总异常实例数")


OP = TypeVar("OP")


@dataclass
class OperationGroup(Generic[OP]):
    latest: Optional[OP] = None
    latest_succeeded: Optional[OP] = None
    pending: Optional[OP] = None


@dataclass
class ModuleState:
    deployment: OperationGroup[Deployment]
    offline: OperationGroup[OfflineOperation]


@dataclass
class ModuleScopedData:
    module_name: str
    build_method: RuntimeType
    state: ModuleState
    exposed_url: Optional[str]
    repo_url: Optional[str]
    version_info: Optional[VersionInfo] = None

    processes: List[Process] = field(default_factory=list)
    instances: List[Instance] = field(default_factory=list)
    proc_specs: List[Dict] = field(default_factory=list)

    @property
    def total_available_instance_count(self) -> int:
        return sum(p.status.success for p in self.processes if p.status)

    @property
    def total_desired_replicas(self) -> int:
        # Q: 为什么不使用 process_specs 的 target_replicas
        # A: 因为该字段对自动扩缩容的进程无效
        return sum(p.status.replicas for p in self.processes if p.status)

    @property
    def total_failed(self) -> int:
        return sum(p.status.failed for p in self.processes if p.status)


class NamespaceScopedListWatchRespSLZ(serializers.Serializer):
    data = NamespaceScopedListWatchRespPartSLZ(many=True)
    rv_proc = serializers.CharField(required=True)
    rv_inst = serializers.CharField(required=True)


class ErrorEventSLZ(serializers.Serializer):
    """SLZ for WatchEvent which type == 'ERROR'"""

    type = serializers.CharField()
    error_message = serializers.CharField()


class WatchEventSLZ(serializers.Serializer):
    """SLZ for ProcessInstanceListWatcher.watch"""

    type = serializers.CharField()
    object_type = serializers.CharField()
    object = serializers.DictField()
    resource_version = serializers.CharField(allow_null=True, help_text="仅 object_type != 'error' 时有该字段")

    def to_representation(self, instance: WatchEvent):
        data: Dict[str, Any] = {"type": instance.type}
        if instance.type == "ERROR":
            data["object_type"] = "error"
            data["object"] = ErrorEventSLZ(instance).data
        if isinstance(instance.res_object, Process):
            data["object_type"] = "process"
            data["object"] = ProcessForDisplaySLZ(instance.res_object).data
            data["resource_version"] = instance.res_object.get_resource_version()
        elif isinstance(instance.res_object, Instance):
            data["object_type"] = "instance"
            data["object"] = InstanceForDisplaySLZ(instance.res_object).data
            data["resource_version"] = instance.res_object.get_resource_version()
        return super().to_representation(data)


class ScalingObjectRefSLZ(serializers.Serializer):
    """资源引用"""

    api_version = serializers.CharField(required=True)
    kind = serializers.CharField(required=True)
    name = serializers.CharField(required=True)


class MetricSpecSLZ(serializers.Serializer):
    """扩缩容指标"""

    type = serializers.ChoiceField(
        required=False,
        default=ScalingMetricSourceType.RESOURCE,
        choices=ScalingMetricSourceType.get_choices(),
    )
    metric = serializers.ChoiceField(required=True, choices=ScalingMetric.get_choices())
    value = serializers.CharField(required=True, help_text=_("资源指标值/百分比"))
    described_object = ScalingObjectRefSLZ(required=False)


class ScalingConfigSLZ(serializers.Serializer):
    """扩缩容配置"""

    min_replicas = serializers.IntegerField(required=True, min_value=1, help_text=_("最小副本数"))
    max_replicas = serializers.IntegerField(required=True, min_value=1, help_text=_("最大副本数"))
    policy = serializers.CharField(required=False, default="default", help_text=_("扩缩容策略"))
    metrics = serializers.ListField(child=MetricSpecSLZ(), required=False, min_length=1, help_text=_("扩缩容指标"))


class ProcessSpecSLZ(serializers.Serializer):
    """Serializer for representing process packages

    Need to convert the resource limit to a number:
    "resource_limit": {
        "cpu": "100m",
        "memory": "64Mi"
    }
    "resource_limit_quota": {
        "cpu": 100,
        "memory": 64
    }
    """

    name = serializers.CharField()
    target_replicas = serializers.IntegerField()
    target_status = serializers.CharField()
    max_replicas = serializers.IntegerField(source="plan.max_replicas")
    resource_limit = serializers.JSONField(source="plan.limits")
    resource_requests = serializers.JSONField(source="plan.requests")
    plan_name = serializers.CharField(source="plan.name")
    resource_limit_quota = serializers.SerializerMethodField(read_only=True)
    autoscaling = serializers.BooleanField()
    scaling_config = ScalingConfigSLZ()

    def get_resource_limit_quota(self, obj: ProcessSpec) -> dict:
        limits = obj.plan.limits
        # 内存的单位为 Mi
        memory_quota = int(parse_quantity(limits["memory"]) / (1024 * 1024))
        # CPU 的单位为 m
        cpu_quota = int(parse_quantity(limits["cpu"]) * 1000)
        return {"cpu": cpu_quota, "memory": memory_quota}


class UpdateProcessSLZ(serializers.Serializer):
    """Serializer for updating processes"""

    process_type = serializers.CharField(required=True)
    operate_type = serializers.ChoiceField(required=True, choices=ProcessUpdateType.get_django_choices())
    target_replicas = serializers.IntegerField(required=False, min_value=1, help_text=_("目标进程副本数"))
    autoscaling = serializers.BooleanField(required=False, default=False, help_text=_("是否开启自动扩缩容"))
    scaling_config = ScalingConfigSLZ(required=False, help_text=_("进程扩缩容配置"))

    def validate(self, attrs: Dict) -> Dict:
        if attrs["operate_type"] == ProcessUpdateType.SCALE:
            if attrs["autoscaling"]:
                if not attrs.get("scaling_config"):
                    raise ValidationError(_("当启用自动扩缩容时，必须提供有效的 scaling_config"))
            elif not attrs.get("target_replicas"):
                raise ValidationError(_("当操作类型为扩缩容时，必须提供有效的 target_replicas"))

        return attrs

    def validate_scaling_config(self, config: Dict) -> Optional[AutoscalingConfig]:
        if not config:
            return None
        try:
            return cattr.structure(config, AutoscalingConfig)
        except Exception as e:
            raise ValidationError(_("scaling_config 配置格式有误：{}").format(e))


class ListProcessesQuerySLZ(serializers.Serializer):
    """Serializer for query params of list API"""

    release_id = serializers.UUIDField(default=None, help_text="用于过滤实例的发布ID")

    def validate_release_id(self, release_id: Optional[UUID]) -> Optional[UUID]:
        """Validate release_id by querying database"""
        if not release_id:
            return None

        try:
            self.context["wl_app"].release_set.get(pk=release_id)
        except Release.DoesNotExist:
            raise ValidationError(f"Release with id={release_id} do not exists")
        return release_id


class WatchProcessesQuerySLZ(serializers.Serializer):
    """Serializer for query params of watch API"""

    timeout_seconds = serializers.IntegerField(required=False, default=30, max_value=120)
    rv_proc = serializers.CharField(required=True)
    rv_inst = serializers.CharField(required=True)


class InstanceLogDownloadInputSLZ(serializers.Serializer):
    """Serializer for instance log download API"""

    previous = serializers.BooleanField(help_text="是否获取上一个实例的日志")


class InstanceLogQueryInputSLZ(serializers.Serializer):
    """Serializer for query params of instance log API"""

    previous = serializers.BooleanField(help_text="是否获取上一个实例的日志")
    tail_lines = serializers.IntegerField(
        required=False, default=400, min_value=1, max_value=10000, help_text="获取日志的行数"
    )


class InstanceLogStreamInputSLZ(serializers.Serializer):
    """Serializer for instance log stream API"""

    since_time = serializers.CharField(required=False, help_text="查询日志的起始时间 (UTC格式)")

    def validate(self, attrs):
        since_time = attrs.get("since_time")
        # 如果没有传递 since_time, 则使用当前时间, 并转化为 RFC3339Nano 字符串
        if not since_time:
            attrs["since_time"] = timezone.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        # 验证是否是合法的时间格式
        try:
            parser.parse(since_time)
        except Exception:
            raise ValidationError({"since_time": "format must be RFC3339Nano"})
        # 验证 since_time 是否是 RFC3339Nano 格式
        rfc3339nano_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})\.(\d{9})Z$")
        if not re.match(rfc3339nano_pattern, since_time):
            raise ValidationError({"since_time": "format must be RFC3339Nano"})

        return attrs
