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

from blue_krill.web.std_error import ErrorCode
from django.utils.translation import gettext_lazy as _


class ErrorCodes:
    # 平台管理员相关
    USER_PROFILE_NOT_FOUND = ErrorCode(_("用户不存在"))

    # 用户特性相关
    USER_FEATURE_FLAG_NOT_FOUND = ErrorCode(_("用户特性不存在"))
    USER_FEATURE_FLAG_ALREADY_EXISTS = ErrorCode(_("用户特性已存在"))

    # 已授权应用相关
    APP_NOT_FOUND = ErrorCode(_("应用不存在"))
    SYSAPI_CLIENT_ROLE_NOT_FOUND = ErrorCode(_("指定的 sysapi client 权限不存在"))
    SYSAPI_CLIENT_NOT_FOUND = ErrorCode(_("请求未携带有效的 sysapi client 信息"))
    APP_AUTHENTICATED_ALREADY_EXISTS = ErrorCode(_("应用已经添加了授权关系"))
    SYSAPI_CLIENT_ALREADY_EXISTS = ErrorCode(_("指定的 sysapi client 已存在"))
    SYSAPI_CLIENT_PERM_DENIED = ErrorCode(_("当前的 sysapi client 无权访问"), status_code=403)

    # 用户与通知相关
    ERROR_SENDING_NOTIFICATION = ErrorCode(_("发送通知消息失败，请稍候重试"))
    NOTIFICATION_DISABLED = ErrorCode(_("暂不支持发送通知"))
    # 人员管理
    MEMBERSHIP_DELETE_FAILED = ErrorCode(_("应用应该至少拥有一个管理员"))
    MEMBERSHIP_CREATE_FAILED = ErrorCode(_("成员创建失败"))
    MEMBERSHIP_OWNER_FAILED = ErrorCode(_("应用所有者不能执行该操作"))
    # 云 API 管理
    QUERY_API_LIST_FAILED = ErrorCode(_("查询API列表失败"))
    CLIENT_CREDENTIALS_MISSING = ErrorCode(_("应用身份凭证缺失"))
    # 应用创建 & 删除
    CANNOT_CREATE_APP = ErrorCode(_("应用创建失败"))
    CANNOT_INIT_APP_TEMPLATE = ErrorCode(_("初始化应用源码模板失败"))
    CANNOT_DELETE_APP = ErrorCode(_("应用删除失败"))
    APP_RES_PROTECTED = ErrorCode(_("访问受保护资源失败"))
    # 模块
    CANNOT_CREATE_MODULE = ErrorCode(_("模块创建失败"))
    CANNOT_SET_DEFAULT = ErrorCode(_("设置默认访问模块失败"))
    CANNOT_DELETE_MODULE = ErrorCode(_("删除模块失败"))
    CREATE_MODULE_QUOTA_EXCEEDED = ErrorCode(_("模块创建数量已达到配额上限"))
    # 进程操作
    CANNOT_OPERATE_PROCESS = ErrorCode(_("操作进程失败"))
    QUERY_PROCESS_FAILED = ErrorCode(_("获取进程信息失败"))
    PROCESS_OPERATION_TOO_OFTEN = ErrorCode(_("进程操作过于频繁，请稍后再试"))
    # 增强服务
    CANNOT_BIND_SERVICE = ErrorCode(_("增强服务绑定失败"), code_num=4313010)
    CANNOT_PROVISION_INSTANCE = ErrorCode(_("配置资源实例失败"), code_num=4313020)
    CANNOT_GET_CLUSTER_INFO = ErrorCode(_("获取集群信息失败"), code_num=4313021)
    RESOURCE_POOL_IS_EMPTY = ErrorCode(_("资源池为空"), code_num=4313022)
    CANNOT_DESTROY_SERVICE = ErrorCode(_("服务删除失败"), code_num=4313040)
    CREATE_SHARED_ATTACHMENT_ERROR = ErrorCode(_("共享增强服务失败"), code_num=4313050)
    CANNOT_DESTROY_CI_RESOURCES = ErrorCode(_("CI相关资源删除失败"), code_num=4313081)
    CANNOT_READ_INSTANCE_INFO = ErrorCode(_("读取增强服务实例信息失败"), code_num=4313082)
    UNSUPPORTED_OPERATION = ErrorCode(_("增强服务暂时不支持该操作"))
    # 部署
    CANNOT_GET_DEPLOYMENT = ErrorCode(_("查询部署信息失败"), code_num=4311001)
    CANNOT_GET_DEPLOYMENT_PHASES = ErrorCode(_("查询部署阶段信息失败"), code_num=4311002)
    CANNOT_DEPLOY_APP = ErrorCode(_("部署失败"), code_num=4311003)
    CANNOT_DEPLOY_ONGOING_EXISTS = ErrorCode(_("部署失败，已有部署任务进行中，请刷新查看"), code_num=4311004)
    APP_NOT_RELEASED = ErrorCode(_("应用尚未在该环境发布过"), code_num=4311005)
    RESTRICT_ROLE_DEPLOY_ENABLED = ErrorCode(_("已开启部署权限控制，仅管理员可以操作"), code_num=4311006)
    CHANNEL_NOT_FOUND = ErrorCode(_("日志流管道不存在"), status_code=404, code_num=4311007)
    DEPLOY_INTERRUPTION_FAILED = ErrorCode(_("中止部署失败"), code_num=4311008)
    # CI
    RESOURCE_NOT_READY_BEFORE_OAUTH = ErrorCode(_("CI 相关资源尚未创建，无法获取授权链接"))
    FAILED_TO_GET_OAUTH_URL = ErrorCode(_("获取授权链接失败"))
    # 代码仓库
    CANNOT_BIND_REPO = ErrorCode(_("仓库绑定失败"), code_num=4312001)
    CANNOT_GET_REPO = ErrorCode(_("无法获取源码信息"), code_num=4312002)
    NEED_TO_BIND_OAUTH_INFO = ErrorCode(_("尚未绑定 OAUTH 授权信息"), code_num=4312003)
    CANNOT_GET_REVISION = ErrorCode(_("无法获取代码版本"), code_num=4312004)
    CANNOT_MODIFY_REPO_BACKEND = ErrorCode(_("无法切换源码仓库类型"), code_num=4312005)
    CANNOT_CREATE_SVN_TAG = ErrorCode(_("无法创建 Svn tag"), code_num=4312006)
    UNSUPPORTED_SOURCE_TYPE = ErrorCode(_("未支持的源码类型"), code_num=4312007)
    UNSUPPORTED_SOURCE_ORIGIN = ErrorCode(_("未支持的源码来源"), code_num=4312008)
    PACKAGE_ALREADY_EXISTS = ErrorCode(_("源码包已存在"), code_num=4312009)
    MISSING_VERSION_INFO = ErrorCode(_("缺失版本信息"), code_num=4312010)
    OBJECT_STORE_EXCEPTION = ErrorCode(_("对象存储服务异常"), code_num=4312011)
    CANNOT_COMMIT_TO_REPOSITORY = ErrorCode(_("代码提交失败"), code_num=4312012)
    # 部署配置
    BIND_RUNTIME_FAILED = ErrorCode(_("绑定运行时失败"), code_num=4313001)
    # 日志
    QUERY_LOG_FAILED = ErrorCode(_("查询日志失败"))
    QUERY_REQUEST_ERROR = ErrorCode(_("查询日志失败，请检查查询条件"))
    CUSTOM_COLLECTOR_NOT_EXISTED = ErrorCode(_("日志平台-「自定义上报」配置不存在"))
    CANNOT_DELETE_CUSTOM_COLLECTOR = ErrorCode(_("删除日志采集规则失败"))
    CUSTOM_COLLECTOR_UNSUPPORTED = ErrorCode(_("暂不支持自定义日志采集"))
    ES_NOT_CONFIGURED = ErrorCode(_("ElasticSearch 未配置"))
    # 权限管理
    CANNOT_MODIFY_ITEM = ErrorCode(_("当前项不允许变更"))
    # 迁移
    APP_NOT_DEPLOYED_IN_ANY_ENV = ErrorCode(_("应用尚未在任何环境部署"))
    LEGACY_MIGRATION_CONFIRMED_FAILED = ErrorCode(_("应用迁移确认, 切换入口失败"))
    APP_NOT_OFFLINE_IN_PAAS3 = ErrorCode(_("应用在新版开发者中心未完全下架"))
    APP_NOT_OFFLINE_IN_PAAS2 = ErrorCode(_("应用在旧版开发者中心未完全下架"))
    APP_MIGRATION_FAILED = ErrorCode(_("应用迁移失败"))
    APP_ROLLBACK_FAILED = ErrorCode(_("应用回滚失败"))
    APP_MIGRATION_CONFIRMED_FAILED = ErrorCode(_("应用迁移确认失败"))
    # 下架
    CANNOT_GET_OFFLINE = ErrorCode(_("查询下线信息失败"))
    CANNOT_OFFLINE_APP = ErrorCode(_("下线失败"))
    # 市场上架
    RELEASED_MARKET_CONDITION_NOT_MET = ErrorCode(_("未满足应用市场服务开启条件"))
    # 资源 Metrics
    APP_METRICS_UNSUPPORTED = ErrorCode(_("应用资源 metrics 暂不支持"))
    CANNOT_FETCH_RESOURCE_METRICS = ErrorCode(_("无法获取应用资源 metrics"))
    # Monitor
    INIT_ALERT_RULES_FAILED = ErrorCode(_("初始化告警规则失败"))
    QUERY_ALERTS_FAILED = ErrorCode(_("查询告警失败"))
    QUERY_ALARM_STRATEGIES_FAILED = ErrorCode(_("查询告警策略失败"))
    # 独立域名
    CANNOT_UPDATE_DOMAIN = ErrorCode(_("无法更新独立域名"))
    CANNOT_CREATE_DOMAIN = ErrorCode(_("无法添加独立域名"))
    CANNOT_DELETE_DOMAIN = ErrorCode(_("无法删除独立域名"))
    # 应用未开启引擎
    ENGINE_DISABLED = ErrorCode(_("应用引擎未开启"))
    # 访问量统计
    REQUEST_PA_FAIL = ErrorCode(_("访问量统计接口异常"))
    ERROR_UPDATING_TRACKING_STATUS = ErrorCode(_("更新统计功能状态失败"))
    # YAML文件导入
    NOT_YAML_FILE = ErrorCode(_("不是yaml文件"))
    ERROR_FILE_FORMAT = ErrorCode(_("文件格式错误"))
    # 文档填写
    DOC_TEMPLATE_ID_NOT_FOUND = ErrorCode(_("文档模板不存在"))
    # S-Mart 应用
    PREPARED_PACKAGE_NOT_FOUND = ErrorCode(_("没找到任何待创建的 S-Mart 应用包"), code_num=4314001)
    PREPARED_PACKAGE_ERROR = ErrorCode(_("预处理 S-Mart 应用包异常"))
    MISSING_DESCRIPTION_INFO = ErrorCode(_("缺失应用描述文件"), code_num=4314002)
    FAILED_TO_HANDLE_APP_DESC = ErrorCode(_("分析应用描述文件异常"), code_num=4314003)
    FAILED_TO_PUSH_IMAGE = ErrorCode(_("访问容器镜像仓库异常"), code_num=4314004)
    FILE_CORRUPTED_ERROR = ErrorCode(_("S-Mart 应用源码文件损坏"))
    # 对外接口异常
    CANNOT_GET_BK_USER_CREDENTIAL = ErrorCode(_("无法获取用户凭证"))
    # Oauth 相关错误
    OAUTH_UNKNOWN_BACKEND_NAME = ErrorCode(_("Oauth 后端类型无效"))
    # Feature Flag 相关错误
    FEATURE_FLAG_DISABLED = ErrorCode(_("暂不支持该功能"))
    # 请求第三方接口错误
    REMOTE_REQUEST_ERROR = ErrorCode(_("请求第三方接口错误"))
    # 云API配置错误
    CLOUDAPI_PATH_ERROR = ErrorCode(_("云API相关接口路径错误"))
    CLOUDAPI_REGION_NOT_FOUND = ErrorCode(_("云API中Region对应的用户类型未配置"))

    # 蓝鲸插件（bk_plugin）相关
    APP_IS_NOT_BK_PLUGIN = ErrorCode(_("应用不是“蓝鲸插件”类型"))
    UNABLE_TO_SET_DISTRIBUTORS = ErrorCode(_("无法设置插件使用方，请稍候重试"))
    # 应用模板相关
    NORMAL_TMPL_NOT_FOUND = ErrorCode(_("指定的应用模板不存在或不可用"))
    UNKNOWN_TEMPLATE = ErrorCode(_("无效的应用模板"))

    # lesscode app 相关
    CREATE_LESSCODE_APP_ERROR = ErrorCode(_("创建蓝鲸运维开发平台应用错误"))

    # Admin 相关
    CONTROLLER_INTERNAL_ERROR = ErrorCode(_("engine 服务错误"))

    # 权限中心相关
    INITIALIZE_APP_MEMBERS_ERROR = ErrorCode(_("初始化应用成员信息失败"))
    CREATE_APP_MEMBERS_ERROR = ErrorCode(_("添加应用成员失败"))
    UPDATE_APP_MEMBERS_ERROR = ErrorCode(_("修改应用成员失败"))
    DELETE_APP_MEMBERS_ERROR = ErrorCode(_("删除应用成员失败"))

    # BCS 组件相关
    EGRESS_SPEC_NOT_FOUND = ErrorCode(_("指定环境的 Egress 配置不存在"))

    # 平台升级提醒
    ACTION_NOT_AVAILABLE = ErrorCode(_("因该功能正在升级改造，操作暂不可用。"), status_code=503)
    MODIFY_UNSUPPORTED = ErrorCode(_("暂不支持修改该配置"))

    # workloads error code
    # Custom Domain Start
    DELETE_CUSTOM_DOMAIN_FAILED = ErrorCode("删除独立域名失败")
    CREATE_CUSTOM_DOMAIN_FAILED = ErrorCode("创建独立域名失败")
    UPDATE_CUSTOM_DOMAIN_FAILED = ErrorCode("修改独立域名失败")

    ERROR_UPDATING_PROC_SERVICE = ErrorCode("无法更新进程服务")
    ERROR_UPDATING_PROC_INGRESS = ErrorCode("无法更新主入口")

    # Credentials
    CREATE_CREDENTIALS_FAILED = ErrorCode("Failed to create credentials")

    # Manifest
    IMPORT_MANIFEST_FAILED = ErrorCode(_("导入应用模型失败"))

    # 应用集群
    CANNOT_CREATE_CLUSTER = ErrorCode(_("无法创建应用集群"))
    CANNOT_UPDATE_CLUSTER = ErrorCode(_("无法更新应用集群"))
    CANNOT_DELETE_CLUSTER = ErrorCode(_("无法删除应用集群"))
    # 集群组件
    CANNOT_UPSERT_CLUSTER_COMPONENT = ErrorCode(_("无法更新集群组件"))

    # dev sandbox
    DEV_SANDBOX_CREATE_FAILED = ErrorCode(_("创建开发沙箱失败"))
    DEV_SANDBOX_ALREADY_EXISTS = ErrorCode(_("开发沙箱已存在"), status_code=409)
    DEV_SANDBOX_NOT_FOUND = ErrorCode(_("指定的开发沙箱不存在"), status_code=404)
    DEV_SANDBOX_COUNT_OVER_LIMIT = ErrorCode(_("开发沙箱总数量超过上限"))
    DEV_SANDBOX_API_ERROR = ErrorCode(_("开发沙箱 API 请求异常"))

    def dump(self, fh=None):
        """A function to dump ErrorCodes as markdown table."""
        attrs = [attr for attr in dir(self) if attr.isupper()]
        table = {}
        for attr in attrs:
            code = getattr(self, attr)
            if code.code_num == -1:
                continue
            table[code.code_num] = code.message

        print(_("| 错误码 | 描述 |"), file=fh)
        print("| - | - |", file=fh)
        for code_num, message in sorted(table.items()):
            print(f"| {code_num} | {message} |", file=fh)


error_codes = ErrorCodes()
