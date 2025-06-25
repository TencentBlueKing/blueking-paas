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

from typing import TYPE_CHECKING, Dict, Optional

from django.db import models
from jsonfield import JSONField

from paas_wl.bk_app.applications.models import UuidAuditedModel
from paas_wl.utils.models import validate_procfile

if TYPE_CHECKING:
    from paas_wl.bk_app.applications.models import Build, Config, WlApp


class ReleaseManager(models.Manager):
    def new(
        self,
        owner: str,
        build: "Build",
        procfile: Dict[str, str],
        summary: Optional[str] = None,
        config: Optional["Config"] = None,
    ):
        """Create a new release

        :param owner str: 发布者, 目前该字段无意义
        :param build 'Build': 应用构建记录
        :param summary str:
        :param config Optional[Config]: 应用配置, 包含环境变量和资源限制等信息. 如果不提供, 则获取上一个发布版本的应用配置
        """
        from paas_wl.bk_app.applications.models import WlApp

        # Get the largest(latest) version and increase it by 1.
        if not hasattr(self, "instance"):
            raise RuntimeError("Only call `new` method from RelatedManager.")

        if not isinstance(self.instance, WlApp):
            raise TypeError("Only call from app.release_set.")

        if build is None:
            raise RuntimeError("No build associated with this release.")

        app = self.instance
        latest_release = self.order_by("-version").first()
        if latest_release:
            new_version = latest_release.version + 1
            cfg = config or latest_release.config
        else:
            new_version = 1
            cfg = config or app.config_set.latest()

        release = Release.objects.create(
            app=app,
            version=new_version,
            summary=summary,
            config=cfg,
            build=build,
            owner=owner,
            procfile=procfile,
        )
        return release

    def any_successful(self, app: "WlApp") -> bool:
        """Check if engine app has any successful releases"""
        # In legacy versions, "workloads" will create an initial release object for
        # apps after creation, the object's "build" field was set to `None` and
        # "version" is 1, it must be excluded or current method will always return
        # true.
        qs = self.get_queryset().exclude(version=1, build=None)
        return qs.filter(app=app, failed=False).exists()

    def get_latest(self, app: "WlApp", ignore_failed: bool = False) -> "Release":
        """获取最后一次发布对象(不管是否成功或失败), 如果不存在, 则根据 allow_null 返回 None 或抛异常.

        :param WlApp app: engine app 对象
        :param bool ignore_failed: 寻找最后一次发布对象时, 是否忽略发布失败
        """
        qs = self.filter(app=app).all()
        if ignore_failed:
            qs = qs.filter(failed=False)

        return qs.latest("version")

    def get_by_version(self, app: "WlApp", version: int) -> "Release":
        """根据指定的 WlApp，Version 获取对应的 Release"""
        return self.get(app=app, version=version)


class Release(UuidAuditedModel):
    """
    Software release deployed by the application platform

    Releases contain a class`Build` and a class`Config`.
    """

    owner = models.CharField(max_length=64)
    app = models.ForeignKey("App", on_delete=models.CASCADE)
    version = models.PositiveIntegerField()
    summary = models.TextField(blank=True, null=True)
    failed = models.BooleanField(default=False)
    procfile = JSONField(default={}, blank=True, validators=[validate_procfile])

    config = models.ForeignKey("Config", on_delete=models.CASCADE)
    build = models.ForeignKey("Build", null=True, on_delete=models.CASCADE)

    objects = ReleaseManager()

    class Meta:
        get_latest_by = "created"
        ordering = ["-created"]
        unique_together = (("app", "version"),)

    def __str__(self):
        return "Release: %s" % self.uuid

    @property
    def region(self):
        return self.app.region

    def fail(self, summary: str):
        self.failed = True
        self.summary = summary
        self.save(update_fields=["failed", "summary", "updated"])

    def get_procfile(self) -> Dict:
        """获取与这个发布对象关联的 procfile"""
        return self.procfile or {}

    def get_envs(self) -> Dict:
        """获取与这个发布对象关联的环境变量"""
        envs = {}
        if self.build:
            envs.update(self.build.get_env_variables())
        envs.update(self.config.envs)
        return envs

    def get_previous(self) -> "Release":
        """获取上一次的 release

        :raise ObjectDoesNotExist: 如果不存在上一次的 release, 则抛该异常
        """
        return Release.objects.filter(app=self.app, version__lt=self.version).latest("version")
