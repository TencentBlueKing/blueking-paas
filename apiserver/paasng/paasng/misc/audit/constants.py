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

from blue_krill.data_types.enum import EnumField, IntStructuredEnum, StrStructuredEnum
from django.utils.translation import gettext_lazy as _


class AccessType(IntStructuredEnum):
    """访问方式"""

    WEB = EnumField(0, label=_("网页"))
    API = EnumField(1, label="API")


class ResultCode(IntStructuredEnum):
    """操作结果"""

    SUCCESS = EnumField(0, label=_("成功"))
    ONGOING = EnumField(1, label=_("执行中"))
    FAILURE = EnumField(-1, label=_("失败"))
    INTERRUPT = EnumField(-2, label=_("中断"))

    @classmethod
    def get_terminated_codes(cls):
        return [cls.SUCCESS, cls.FAILURE, cls.INTERRUPT]


class DataType(StrStructuredEnum):
    """记录操作前后数据的数据类型，前端会根据该字段做不同的展示
    前端不需要展示相关的 label, 故不用做国际化标记
    """

    RAW_DATA = EnumField("raw_data", label="原始数据，前端直接渲染即可")
    BKAPP_REVERSION = EnumField("bkapp_revision", label="bkapp.yaml 的版本号，需要通过版本号查询具体的 yaml 内容展示")
    CLOUD_API_RECORD = EnumField(
        "cloud_api_record", label="云 API 权限申请记录 ID, 需要通过 ID 查询具体的申请单据详情展示"
    )
    ESB_API_RECORD = EnumField(
        "esb_api_record", label="组件 API 权限申请记录 ID, 需要通过 ID 查询具体的申请单据详情展示"
    )


class OperationTarget(StrStructuredEnum):
    """操作对象"""

    APP = EnumField("app", label=_("应用"))
    MODULE = EnumField("module", label=_("模块"))
    PROCESS = EnumField("process", label=_("进程"))
    ENV_VAR = EnumField("env_var", label=_("环境变量"))
    ADD_ON = EnumField("addon", label=_("增强服务"))
    CLOUD_API = EnumField("cloud_api", label=_("云 API 权限"))
    SECRET = EnumField("secret", label=_("密钥"))
    APP_DOMAIN = EnumField("app_domain", label=_("访问地址"))
    APP_MEMBER = EnumField("app_member", label=_("应用成员"))
    BUILD_CONFIG = EnumField("build_config", label=_("构建配置"))
    VOLUME_MOUNT = EnumField("volume_mount", label=_("挂载卷"))
    SERVICE_DISCOVERY = EnumField("service_discovery", label=_("服务发现"))
    DOMAIN_RESOLUTION = EnumField("domain_resolution", label=_("域名解析"))
    DEPLOY_RESTRICTION = EnumField("deploy_restriction", label=_("部署限制"))
    EXIT_IP = EnumField("exit_ip", label=_("出口 IP"))
    ACCESS_CONTROL = EnumField("access_control", label=_("用户限制"))
    ACCESS_TOKEN = EnumField("access_token", label=_("访问令牌"))

    # 以下是仅用于 Admin42 的操作对象
    CLUSTER = EnumField("cluster", label=_("集群"))
    CLUSTER_COMPONENT = EnumField("cluster_component", label=_("集群组件"))
    PROCESS_SPEC_PLAN = EnumField("process_spec_plan", label=_("应用资源方案"))
    BKPLUGIN_TAG = EnumField("bkplugin_tag", label=_("插件分类"))
    BKPLUGIN_DISTRIBUTOR = EnumField("bkplugin_distributor", label=_("插件使用方"))
    BKPLUGIN_MEMBER = EnumField("bkplugin_member", label=_("插件成员"))
    DOCUMENT = EnumField("document", label=_("文档"))
    DEPLOY_FAILURE_TIPS = EnumField("deploy_failure_tips", label=_("部署失败提示"))
    SOURCE_TYPE_SPEC = EnumField("source_type_spec", label=_("代码库配置"))
    SHARED_CERT = EnumField("shared_cert", label=_("共享证书"))
    ADDON_PLAN = EnumField("addon_plan", label=_("增强服务方案"))
    PLAT_USER = EnumField("plat_user", label=_("平台用户"))
    FEATURE_FLAG = EnumField("feature_flag", label=_("特性标记"))
    EGRESS_SPEC = EnumField("egress_spec", label=_("Egress 配置"))
    TEMPLATE = EnumField("template", label=_("模板"))
    DASHBOARD_TEMPLATE = EnumField("dashboard_template", label=_("仪表盘模板"))
    BUILDPACK = EnumField("buildpack", label="Buildpack")
    SLUGBUILDER = EnumField("slugbuilder", label="Slugbuilder")
    SLUGRUNNER = EnumField("slugrunner", label="Slugrunner")


class OperationEnum(StrStructuredEnum):
    """操作类型"""

    CREATE = EnumField("create", label=_("新建"))
    DELETE = EnumField("delete", label=_("删除"))
    MODIFY = EnumField("modify", label=_("修改"))
    REFRESH = EnumField("refresh", label=_("刷新"))
    # 直接操作应用相关的类型，展示的文案包括完整的动宾短语
    CREATE_APP = EnumField("create_app", label=_("创建应用"))
    RELEASE_TO_MARKET = EnumField("online_to_market", label=_("发布到应用市场"))
    OFFLINE_MARKET = EnumField("offline_from_market", label=_("从应用市场下架"))
    MODIFY_MARKET_INFO = EnumField("modify_market_info", label=_("完善应用市场配置"))
    MODIFY_MARKET_URL = EnumField("modify_market_url", label=_("修改应用市场访问地址"))
    MODIFY_BASIC_INFO = EnumField("modify_basic_info", label=_("修改基本信息"))
    # 进程相关操作
    START = EnumField("start", label=_("启动"))
    STOP = EnumField("stop", label=_("停止"))
    SCALE = EnumField("scale", label=_("扩缩容"))
    ENABLE = EnumField("enable", label=_("启用"))
    DISABLE = EnumField("disable", label=_("停用"))
    APPLY = EnumField("apply", label=_("申请"))
    RENEW = EnumField("renew", label=_("续期"))
    DEPLOY = EnumField("deploy", label=_("部署"))
    OFFLINE = EnumField("offline", label=_("下架"))
    # 以下是仅用于 Admin42 的操作对象
    MODIFY_PLAN = EnumField("switch", label=_("切换资源方案"))
    MODIFY_USER_FEATURE_FLAG = EnumField("modify_user_feature_flag", label=_("修改用户特性"))
    SWITCH_DEFAULT_CLUSTER = EnumField("switch_default_cluster", label=_("切换默认集群"))
    BIND_CLUSTER = EnumField("bind_cluster", label=_("切换绑定集群"))
    MODIFY_LOG_CONFIG = EnumField("modify_log_config", label=_("日志采集管理"))
    PROVISION_INSTANCE = EnumField("provision_instance", label=_("分配增强服务实例"))
    RECYCLE_RESOURCE = EnumField("recycle_resource", label=_("回收增强服务实例"))
