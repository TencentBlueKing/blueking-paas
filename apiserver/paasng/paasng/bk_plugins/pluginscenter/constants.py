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

from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.utils.translation import gettext_lazy as _


class PluginReleaseMethod(str, StructuredEnum):
    """插件发布方式"""

    CODE = EnumField("code", label="源码发布")
    SOURCE_PACKAGE = EnumField("sourcePackage", label="源码包发布")
    IMAGE = EnumField("image", label="镜像发布")


class PluginBasicInfoAccessMode(str, StructuredEnum):
    """插件基本信息查看模式"""

    READONLY = EnumField("readonly", label="只读")
    READWRITE = EnumField("readwrite", label="读写")


class PluginReleaseVersionRule(str, StructuredEnum):
    """插件发布版本号规则"""

    AUTOMATIC = EnumField("automatic", label="自动生成 semver")
    REVISION = EnumField("revision", label="与代码分支一致")
    COMMIT_HASH = EnumField("commit-hash", label="与提交哈希一致")
    BRANCH_TIMESTAMP = EnumField("branch-timestamp", label="代码分支+时间戳")
    SELF_FILL = EnumField("self-fill", label="用户自助填写")


class SemverAutomaticType(str, StructuredEnum):
    """语义化版本生成规则"""

    MAJOR = EnumField("major", label="重大版本")
    MINOR = EnumField("minor", label="次版本")
    PATCH = EnumField("patch", label="修正版本")


class ReleaseStageInvokeMethod(str, StructuredEnum):
    """发布步骤触发方式"""

    DEPLOY_API = EnumField("deployAPI", label="部署接口")
    PIPELINE = EnumField("pipeline", label="流水线")
    SUBPAGE = EnumField("subpage", label="子页面")
    ITSM = EnumField("itsm", label="itsm 审批流程")
    CANARY_WITH_ITSM = EnumField("canaryWithItsm", label="带审批的灰度发布")
    BUILTIN = EnumField("builtin", label="内置功能(完善市场信息market, 灰度grayScale, 上线online)")


class PluginStatus(str, StructuredEnum):
    """插件状态"""

    WAITING_APPROVAL = EnumField("waiting-approval", label="创建审批中")
    APPROVAL_FAILED = EnumField("approval-failed", label="创建审批失败")
    DEVELOPING = EnumField("developing", label="开发中")
    RELEASING = EnumField("releasing", label="发布中")
    RELEASED = EnumField("released", label="已发布")
    # 后台轮询下架进度, 进入「下架」相关的状态后, 插件还可以进行相关操作
    ARCHIVED = EnumField("archived", label="已下架")

    @classmethod
    def archive_status(cls):
        """下架相关的状态"""
        return [cls.ARCHIVED]

    @classmethod
    def approval_status(cls):
        return [cls.APPROVAL_FAILED, cls.WAITING_APPROVAL]


class PluginRole(int, StructuredEnum):
    """插件角色"""

    ADMINISTRATOR = EnumField(2, label="管理员")
    DEVELOPER = EnumField(3, label="开发者")


class MarketInfoStorageType(str, StructuredEnum):
    """市场信息存储类型"""

    THIRD_PARTY = EnumField("third-party", label="仅存储在第三方系统")
    PLATFORM = EnumField("platform", label="仅存储在插件开发中心")
    BOTH = EnumField("both", label="同时存储在插件开发中心和第三方系统")


class PluginReleaseStatus(str, StructuredEnum):
    """插件发布状态"""

    SUCCESSFUL = EnumField("successful", label="成功")
    FAILED = EnumField("failed", label="失败")
    PENDING = EnumField("pending", label="等待")
    INITIAL = EnumField("initial", label="初始化")
    INTERRUPTED = EnumField("interrupted", label="已中断")

    @classmethod
    def abnormal_status(cls):
        return [cls.FAILED, cls.INTERRUPTED]

    @classmethod
    def running_status(cls):
        return [cls.INITIAL, cls.PENDING]

    @classmethod
    def terminated_status(cls):
        return [cls.FAILED, cls.INTERRUPTED, cls.SUCCESSFUL]


class LogTimeChoices(str, StructuredEnum):
    """日志搜索-日期范围可选值"""

    FIVE_MINUTES = EnumField("5m", label="5分钟")
    ONE_HOUR = EnumField("1h", label="1小时")
    THREE_HOURS = EnumField("3h", label="3小时")
    SIX_HOURS = EnumField("6h", label="6小时")
    TWELVE_HOURS = EnumField("12h", label="12小时")
    ONE_DAY = EnumField("1d", label="1天")
    THREE_DAYS = EnumField("3d", label="3天")
    SEVEN_DAYS = EnumField("7d", label="7天")
    CUSTOMIZED = EnumField("customized", label="自定义")


class ActionTypes(str, StructuredEnum):
    """操作记录-动作类型"""

    CREATE = EnumField("create", label=_("创建"))
    ADD = EnumField("add", label=_("新建"))
    RE_RELEASE = EnumField("re-release", label=_("重新发布"))
    TERMINATE = EnumField("terminate", label=_("终止发布"))
    MODIFY = EnumField("modify", label=_("修改"))
    DELETE = EnumField("delete", label=_("删除"))
    ARCHIVE = EnumField("archive", label=_("下架"))
    REACTIVATE = EnumField("reactivate", label=_("重新上架"))
    ROLLBACK = EnumField("rollback", label=_("回滚"))


class SubjectTypes(str, StructuredEnum):
    """操作记录-主体"""

    PLUGIN = EnumField("plugin", label=_("插件"))
    TEST_VERSION = EnumField("test_version", label=_("测试版本"))
    VERSION = EnumField("version", label=_("版本"))
    BASIC_INFO = EnumField("basic_info", label=_("基本信息"))
    LOGO = EnumField("logo", label=_("logo"))
    MARKET_INFO = EnumField("market_info", label=_("市场信息"))
    CONFIG_INFO = EnumField("config_info", label=_("配置信息"))
    VISIBLE_RANGE = EnumField("visible_range", label=_("可见范围"))
    PUBLISHER = EnumField("publisher", label=_("发布者"))
    RELEASE_STRATEGY = EnumField("release_strategy", label=_("发布策略"))


class PluginReleaseType(str, StructuredEnum):
    """插件版本发布类型"""

    PROD = EnumField("prod", label=_("正式发布"))
    TEST = EnumField("test", label=_("测试发布"))


class ReleaseStrategy(str, StructuredEnum):
    """插件发布策略"""

    GRAY = EnumField("gray", label=_("灰度发布"))
    FULL = EnumField("full", label=_("全量发布"))


class StatusPollingMethod(str, StructuredEnum):
    """发布阶段的状态轮询方式"""

    API = EnumField("api", label=_("后台 API 轮询"))
    FRONTEND = EnumField("frontend", label=_("前端轮询，如通过 Iframe message 通信等"))


class PluginRevisionType(str, StructuredEnum):
    """代码版本类型"""

    ALL = EnumField("all", label=_("不限制"))
    MASTER = EnumField("master", label=_("仅可选择主分支发布"))
    TAG = EnumField("tag", label=_("Tag 发布"))
    TESTED_VERSION = EnumField("tested_version", label=_("已经测试通过的版本"))


class GrayReleaseStatus(str, StructuredEnum):
    """插件灰度发布展示的状态，提供给前端展示的字段不需要国际化标记"""

    GRAY_APPROVAL_IN_PROGRESS = EnumField("gray_approval_in_progress", label="灰度发布审批中")
    IN_GRAY = EnumField("in_gray", label="灰度中")
    GRAY_APPROVAL_FAILED = EnumField("gray_approval_failed", label="灰度审批失败")
    FULL_APPROVAL_IN_PROGRESS = EnumField("full_approval_in_progress", label="全量发布审批中")
    FULLY_RELEASED = EnumField("fully_released", label="已全量发布")
    FULL_APPROVAL_FAILED = EnumField("full_approval_failed", label="全量发布审批失败")
    ROLLED_BACK = EnumField("rolled_back", label="已回滚")
    INTERRUPTED = EnumField("interrupted", label="已终止")
