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

from typing import List

from blue_krill.data_types.enum import EnumField, StrStructuredEnum
from django.utils.translation import gettext_lazy as _

from paasng.utils.basic import ChoicesEnum

PROC_DEFAULT_REPLICAS = 1
DOCKER_BUILD_STEPSET_NAME = "docker-build"
IMAGE_RELEASE_STEPSET_NAME = "image-release"


class AppEnvName(StrStructuredEnum):
    """The default environment names"""

    STAG = EnumField("stag", label=_("预发布环境"))
    PROD = EnumField("prod", label=_("生产环境"))


class JobStatus(StrStructuredEnum):
    SUCCESSFUL = EnumField("successful", label="成功")
    FAILED = EnumField("failed", label="失败")
    PENDING = EnumField("pending", label="等待")
    INTERRUPTED = EnumField("interrupted", label="已中断")

    @classmethod
    def get_finished_states(cls) -> List[str]:
        """获取已完成的状态"""
        return [cls.FAILED, cls.SUCCESSFUL, cls.INTERRUPTED]


class BuildStatus(StrStructuredEnum):
    """While `BuildStatus` has same members with `JobStatus`, different statuses might be added in the future"""

    SUCCESSFUL = "successful"
    FAILED = "failed"
    PENDING = "pending"
    INTERRUPTED = "interrupted"

    @classmethod
    def get_finished_states(cls) -> List[str]:
        """获取已完成的状态"""
        return [cls.FAILED, cls.SUCCESSFUL, cls.INTERRUPTED]


class ReleaseStatus(StrStructuredEnum):
    """While `ReleaseStatus` has same members with `JobStatus`, different statuses might be added in the future"""

    SUCCESSFUL = "successful"
    FAILED = "failed"
    PENDING = "pending"
    INTERRUPTED = "interrupted"

    def to_job_status(self) -> JobStatus:
        """Transform to `JobStatus`"""
        # Do type transformation directly because two types are sharing the same
        # members currently.
        return JobStatus(self.value)


class OperationTypes(ChoicesEnum):
    OFFLINE = "offline"
    ONLINE = "online"

    _choices_labels = (
        (OFFLINE, "下架"),
        (ONLINE, "部署"),
    )


class LBPlans(ChoicesEnum):
    LBDefaultPlan = "LBDefaultPlan"

    _choices_labels = ((LBDefaultPlan, "requests from bk lb to bk cluster"),)


lbplan_2_prefix_mapper = {LBPlans.LBDefaultPlan.value: "defaultplan_prefix"}


class MetricsType(ChoicesEnum):
    MEM = "mem"
    CPU = "cpu"
    __ALL__ = "__all__"

    _choices_labels = ((MEM, "mem"), (CPU, "cpu"), (__ALL__, "__all__"))


class ConfigVarEnvName(StrStructuredEnum):
    """Environment name for managing config var"""

    STAG = EnumField("stag", label="仅测试环境")
    PROD = EnumField("prod", label="仅生产环境")
    GLOBAL = EnumField("_global_", label="所有环境")


class DeployConditions(ChoicesEnum):
    """部署条件类型"""

    FILL_PRODUCT_INFO = "FILL_PRODUCT_INFO"
    CHECK_ENV_PROTECTION = "CHECK_ENV_PROTECTION"
    NEED_TO_BIND_OAUTH_INFO = "NEED_TO_BIND_OAUTH_INFO"
    DONT_HAVE_ENOUGH_PERMISSIONS = "DONT_HAVE_ENOUGH_PERMISSIONS"
    NEED_TO_CORRECT_REPO_INFO = "NEED_TO_CORRECT_REPO_INFO"
    NEED_TO_COMPLETE_PROCFILE = "NEED_TO_COMPLETE_PROCFILE"
    CHECK_CI_GIT_TOKEN = "CHECK_CI_GIT_TOKEN"
    FILL_PLUGIN_TAG_INFO = "FILL_PLUGIN_TAG_INFO"
    FILL_EXTRA_INFO = "FILL_EXTRA_INFO"
    CHECK_OPERATOR_VERSION = "CHECK_OPERATOR_VERSION"

    _choices_labels = (
        (FILL_PRODUCT_INFO, _("未完善应用市场信息")),
        (CHECK_ENV_PROTECTION, _("当前用户无部署该环境的权限")),
        (NEED_TO_BIND_OAUTH_INFO, _("当前用户尚未绑定 OAUTH 授权信息")),
        (DONT_HAVE_ENOUGH_PERMISSIONS, _("当前用户没有访问源码仓库的权限")),
        (NEED_TO_CORRECT_REPO_INFO, _("当前源码仓库信息异常")),
        (NEED_TO_COMPLETE_PROCFILE, _("未完善进程启动命令")),
        (CHECK_CI_GIT_TOKEN, _("当前用户未授权 CI 组件访问仓库的权限")),
        (FILL_PLUGIN_TAG_INFO, _("未设置插件分类")),
        (FILL_EXTRA_INFO, _("未完善应用基本信息")),
        (CHECK_OPERATOR_VERSION, _("Operator 版本不匹配")),
    )


class RuntimeType(StrStructuredEnum):
    BUILDPACK = EnumField("buildpack", label=_("使用 Buildpacks 构建"))
    DOCKERFILE = EnumField("dockerfile", label=_("使用 Dockerfile 构建"))
    CUSTOM_IMAGE = EnumField("custom_image", label="Custom Image(云原生和旧镜像应用)")
