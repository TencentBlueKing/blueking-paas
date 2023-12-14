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
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import cattr
from attrs import define
from django.db import models
from jsonfield import JSONField

from paasng.misc.metrics import DEPLOYMENT_STATUS_COUNTER, DEPLOYMENT_TIME_CONSUME_HISTOGRAM
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.engine.constants import BuildStatus, ImagePullPolicy, JobStatus
from paasng.platform.engine.models.base import OperationVersionBase
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.modules.models.deploy_config import HookList, HookListField
from paasng.platform.sourcectl.models import VersionInfo
from paasng.utils.models import make_json_field, make_legacy_json_field

logger = logging.getLogger(__name__)


class DeploymentQuerySet(models.QuerySet):
    """Custom QuerySet for Deployment model"""

    def filter_by_env(self, env: ModuleEnvironment):
        """Get all deploys under an env"""
        return self.filter(app_environment=env)

    def owned_by_module(self, module, environment=None):
        """Return deployments owned by module"""
        envs = module.get_envs(environment=environment)
        return self.filter(app_environment__in=envs)

    def latest_succeeded(self):
        """Return the latest succeeded deployment of queryset"""
        return self.filter(status=JobStatus.SUCCESSFUL.value).latest("created")


@define
class AdvancedOptions:
    dev_hours_spent: Optional[float] = None
    source_dir: str = ""
    image_pull_policy: ImagePullPolicy = ImagePullPolicy.IF_NOT_PRESENT
    # 只构建, 不发布
    build_only: bool = False
    # 构建的镜像 tag, 将覆盖默认规则
    special_tag: Optional[str] = None
    # 直接发布历史 build
    build_id: Optional[str] = None
    # 触发消息
    invoke_message: Optional[str] = None


@dataclass
class AutoscalingConfig:
    """This class is a duplication of paas_wl.workloads.autoscaling.entities.AutoscalingConfig, it
    avoids a circular import problem.
    """

    # 最小副本数量
    min_replicas: int
    # 最大副本数量
    max_replicas: int
    # 扩缩容策略
    policy: str


@dataclass
class ProcessTmpl:
    """This class is a duplication of paas_wl.bk_app.processes.models.ProcessTmpl, it
    avoids a circular import problem.
    """

    name: str
    command: str
    replicas: Optional[int] = None
    plan: Optional[str] = None
    autoscaling: bool = False
    scaling_config: Optional[AutoscalingConfig] = None

    def __post_init__(self):
        self.name = self.name.lower()


AdvancedOptionsField = make_legacy_json_field(cls_name="AdvancedOptionsField", py_model=AdvancedOptions)
DeclarativeProcessField = make_json_field("DeclarativeProcessField", Dict[str, ProcessTmpl])


class Deployment(OperationVersionBase):
    """部署记录"""

    app_environment = models.ForeignKey(
        "applications.ApplicationEnvironment", on_delete=models.CASCADE, related_name="deployments", null=True
    )
    status = models.CharField(
        "部署状态", choices=JobStatus.get_choices(), max_length=16, default=JobStatus.PENDING.value
    )

    # Related with engine
    build_process_id = models.UUIDField(max_length=32, null=True)
    build_id = models.UUIDField(max_length=32, null=True)
    build_status = models.CharField(choices=BuildStatus.get_choices(), max_length=16, default=BuildStatus.PENDING)
    build_int_requested_at = models.DateTimeField(null=True, help_text="用户请求中断 build 的时间")
    pre_release_id = models.UUIDField(max_length=32, null=True)
    pre_release_status = models.CharField(
        choices=JobStatus.get_choices(), max_length=16, default=JobStatus.PENDING.value
    )
    pre_release_int_requested_at = models.DateTimeField(null=True, help_text="用户请求中断 pre-release 的时间")
    release_id = models.UUIDField(max_length=32, null=True)
    bkapp_release_id = models.BigIntegerField(null=True, help_text="云原生应用发布记录ID")
    release_status = models.CharField(choices=JobStatus.get_choices(), max_length=16, default=JobStatus.PENDING.value)
    release_int_requested_at = models.DateTimeField(null=True, help_text="用户请求中断 release 的时间")

    err_detail = models.TextField("部署异常原因", null=True, blank=True)
    advanced_options: AdvancedOptions = AdvancedOptionsField("高级选项", null=True)

    procfile = JSONField(
        default=dict,
        help_text="[deprecated] 启动命令, 在准备阶段 PaaS 会从源码(或配置)读取应用的 procfile, 并更新该字段, 在发布阶段将从该字段读取 procfile",
    )
    processes = DeclarativeProcessField(
        default=dict,
        help_text="进程定义，在准备阶段 PaaS 会从源码(或配置)读取应用的启动进程, 并更新该字段。在发布阶段会从该字段读取 procfile 和同步 ProcessSpec",
    )
    hooks: HookList = HookListField(help_text="部署钩子", default=list)
    bkapp_revision_id = models.IntegerField(help_text="本次发布指定的 BkApp Revision id", null=True)
    # The fields that store deployment logs, related to the `OutputStream` model. These fields exist
    # because some logs cannot be written to the "build_process" or "pre_release" objects's output streams,
    # such as logs of the service provision actions and hook command executions from cloud-native applications.
    preparation_stream_id = models.UUIDField(help_text="the logs at the preparation phase", max_length=32, null=True)
    main_stream_id = models.UUIDField(help_text="the logs at the main phase", max_length=32, null=True)

    objects = DeploymentQuerySet().as_manager()

    def __str__(self):
        return "{app_code}-{region}-{process}-{status}".format(
            app_code=self.get_application().code,
            region=self.get_application().region,
            process=self.build_process_id,
            status=self.status,
        )

    def update_fields(self, **u_fields):
        logger.info("update_fields, deployment_id: %s, fields: %s", self.id, u_fields)
        before_time = self.updated
        kind: Optional[str]
        status: Optional[JobStatus]
        if "release_status" in u_fields:
            kind = "release"
            status = JobStatus(u_fields["release_status"])
        elif "build_status" in u_fields:
            kind = "build"
            status = JobStatus(u_fields["build_status"])
        else:
            kind = None
            status = None

        for key, value in u_fields.items():
            setattr(self, key, value)
        self.save()

        if kind and status in JobStatus.get_finished_states():
            DEPLOYMENT_STATUS_COUNTER.labels(kind=kind, status=status.value).inc()
            total_seconds = (self.updated - before_time).total_seconds()
            logger.info(f"update_release {total_seconds}")
            DEPLOYMENT_TIME_CONSUME_HISTOGRAM.labels(
                language=self.app_environment.application.language, kind=kind, status=status.value
            ).observe(total_seconds)

    def get_engine_app(self):
        return self.app_environment.get_engine_app()

    def get_application(self):
        return self.app_environment.application

    def fail_with_error(self, err_detail, status=None):
        self.update_fields(err_detail=err_detail, status=status or self.status)

    def get_source_dir(self) -> Path:
        """获取源码目录"""
        if not self.advanced_options:
            return Path(".")
        path = Path(self.advanced_options.source_dir)
        if path.is_absolute():
            logger.warning("Unsupported absolute path<%s>, force transform to relative_to path.", path)
            path = path.relative_to("/")
        return path

    def has_succeeded(self):
        return self.status == JobStatus.SUCCESSFUL.value

    @property
    def has_requested_int(self) -> bool:
        """If an interruption request has been made"""
        return bool(self.build_int_requested_at or self.release_int_requested_at)

    @property
    def start_time(self) -> Optional[str]:
        """获取部署阶段开始时间"""
        # Deployment 肯定是以 PREPARATION 开始
        from paasng.platform.engine.models.phases import DeployPhaseTypes

        try:
            return self.deployphase_set.get(type=DeployPhaseTypes.PREPARATION.value).start_time
        except Exception:
            # 防御，避免绑定阶段中访问此 API 异常
            logger.warning("failed to get PREPARATION start time from deployment<%s>", self.pk)
            return None

    @property
    def complete_time(self) -> Optional[str]:
        """获取部署阶段结束时间"""
        # 但是可能以任意状态结束
        try:
            return (
                self.deployphase_set.filter(status__in=JobStatus.get_finished_states())
                .order_by("-complete_time")
                .first()
                .complete_time
            )
        except Exception:
            logger.warning("failed to get complete status from deployment<%s>", self.pk)
            return None

    @property
    def finished_status(self) -> Optional[str]:
        """获取最后结束的阶段状态"""
        try:
            return (
                self.deployphase_set.filter(status__in=JobStatus.get_finished_states())
                .order_by("-complete_time")
                .first()
                .type
            )
        except Exception:
            logger.warning("failed to get complete status from deployment<%s>", self.pk)
            return None

    def get_version_info(self) -> VersionInfo:
        """获取源码的版本信息, 对于发布 "已构建镜像" 的部署操作, 获取构建该镜像时的版本信息

        :raise ValueError: 当无法获取到版本信息时抛此异常
        """
        module = self.app_environment.module
        # s-mart 镜像应用, 对平台而言还是源码包部署
        if self.source_version_type != "image" or module.source_origin == SourceOrigin.S_MART:
            version_type = self.source_version_type
            version_name = self.source_version_name
            # Backward compatibility
            if not (version_type and version_name):
                version_name = self.source_location.split("/")[-1]
                version_type = "trunk" if version_name == "trunk" else self.source_location.split("/")[-2]
            return VersionInfo(self.source_revision, version_name, version_type)

        # 查询第一个引用 build_id 的 Deployment
        ref = Deployment.objects.filter(build_id=self.build_id).exclude(id=self.id).order_by("created").first()
        if not ref or ref.source_version_type == "image":
            raise ValueError("unknown version info")
        return ref.get_version_info()

    @property
    def version_info(self):
        """Deprecated
        TODO:
        - 获取源码版本的 version_info 替换成 get_version_info()
        - 获取镜像版本的 version_info 需要增加新的函数
        """
        return VersionInfo(self.source_revision, self.source_version_name, self.source_version_type)

    def get_deploy_hooks(self) -> HookList:
        try:
            hooks = self.declarative_config.get_deploy_hooks()
        except Exception:
            hooks = HookList()

        for hook in self.hooks:
            if hook.enabled:
                hooks.upsert(hook.type, hook.command)
        return hooks

    def get_processes(self) -> List[ProcessTmpl]:
        if self.processes:
            return list(self.processes.values())
        # 兼容旧字段 procfile
        # 当使用 procfile 时只会创建 process spec, 不会更新 plan/replicas,scaling_config
        elif self.procfile:
            return cattr.structure(
                [{"name": name, "command": command} for name, command in self.procfile.items()],
                List[ProcessTmpl],
            )
        return []
