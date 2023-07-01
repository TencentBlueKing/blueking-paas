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
from blue_krill.web.std_error import APIError, ErrorCode  # noqa


class ErrorCodes:
    APP_ALREADY_EXISTS = ErrorCode('创建失败，名称为 %(name)s 的应用已经存在。')
    APP_NEVER_RELEASED = ErrorCode('操作失败，应用从未部署过。')
    K8S_SERVICE_UNAVAILABLE = ErrorCode('无法访问 Kubernetes 集群，请稍后重试。')
    PROCESS_OPERATE_FAILED = ErrorCode('进程操作失败')
    ENGINE_NOT_IMPLEMENTED = ErrorCode('Engine尚未提供该接口', status_code=501)
    UPDATE_CONFIG_FAILED = ErrorCode('更新Config失败')
    APP_DELETE_FAILED = ErrorCode('应用删除失败')

    APP_RELEASE_FAILED = ErrorCode('Failed to release app')
    APP_ARCHIVE_FAILED = ErrorCode('Failed to archive App')

    # RegionClusterState start
    CREATE_RCSTATE_BINDING_ERROR = ErrorCode('应用绑定集群状态失败')

    # New error codes for end-user views
    ERROR_ACQUIRING_EGRESS_GATEWAY_INFO = ErrorCode('无法获取出口 IP 信息')
    ERROR_RECYCLING_EGRESS_GATEWAY_INFO = ErrorCode('无法清除出口 IP 信息')
    # RegionClusterState end

    # Services start
    UPDATE_PROC_SERVICE_ERROR = ErrorCode('修改进程服务失败')
    PROC_INGRESS_NOT_FOUND = ErrorCode('未找到访问入口')
    UPDATE_PROC_INGRESS_ERROR = ErrorCode('修改访问入口失败')
    UPDATE_APP_DOMAINS_ERROR = ErrorCode('设置应用域名失败')
    SYNC_INGRESSES_ERROR = ErrorCode('刷新应用入口配置失败')

    # New error codes for end-user views
    ERROR_UPDATING_PROC_SERVICE = ErrorCode('无法更新进程服务')
    ERROR_UPDATING_PROC_INGRESS = ErrorCode('无法更新主入口')

    # Process related codes
    CANNOT_OPERATE_PROCESS = ErrorCode('操作进程失败')
    PROCESS_OPERATION_TOO_OFTEN = ErrorCode('进程操作过于频繁，请稍后再试')

    # Services end
    # Resource Metrics Start
    QUERY_RESOURCE_METRIC_FAILED = ErrorCode('获取应用资源 metrics 失败')
    # Custom Domain Start
    DELETE_CUSTOM_DOMAIN_FAILED = ErrorCode('删除独立域名失败')
    CREATE_CUSTOM_DOMAIN_FAILED = ErrorCode('创建独立域名失败')
    UPDATE_CUSTOM_DOMAIN_FAILED = ErrorCode('修改独立域名失败')

    # sub-domain and subpaths
    SUBPATH_NO_RULES_ERROR = ErrorCode('无法创建子路径规则，缺少必要配置')
    # Edition Start
    EDITION_NOT_SUPPORT = ErrorCode('该功能当前版本不支持')

    # Build Processes
    INTERRUPTION_NOT_ALLOWED = ErrorCode('任务正处于预备执行状态，无法中断，请稍候重试')
    INTERRUPTION_FAILED = ErrorCode('中断失败')

    # System
    SERVICE_AUTH_FAILED = ErrorCode(
        "Authentication between services failed: token is invalid, please contact system admin", status_code=401
    )

    # 平台升级提醒
    ACTION_NOT_AVAILABLE = ErrorCode('因该功能正在升级改造，操作暂不可用。', status_code=503)

    # cnative
    DEPLOY_BKAPP_FAILED = ErrorCode('Failed to deploy bkapp')
    GET_MRES_FAILED = ErrorCode("Failed to find bkapp in Kubernetes")
    INVALID_MRES = ErrorCode("The bkapp is invalid")
    GET_DEPLOYMENT_FAILED = ErrorCode("Failed to find deployed version")

    # Credentials
    CREATE_CREDENTIALS_FAILED = ErrorCode("Failed to create credentials")

    # 集群组件相关
    CLUSTER_COMPONENT_CONFLICT = ErrorCode('Cluster component conflict')
    CLUSTER_COMPONENT_NOT_EXIST = ErrorCode('Cluster component not exist')


error_codes = ErrorCodes()
