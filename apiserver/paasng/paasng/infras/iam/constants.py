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
from blue_krill.data_types.enum import StructuredEnum

from paasng.platform.applications.constants import ApplicationRole

# 使用 -1 表示永不过期
NEVER_EXPIRE_DAYS = -1

# 永不过期的时间（伪，其实是 2100.01.01 08:00:00，与权限中心保持一致)
NEVER_EXPIRE_TIMESTAMP = 4102444800

# 每一天的秒数
ONE_DAY_SECONDS = 24 * 60 * 60

# 默认为每个 APP 创建 3 个用户组，分别是管理者，开发者，运营者
APP_DEFAULT_ROLES = [ApplicationRole.ADMINISTRATOR, ApplicationRole.DEVELOPER, ApplicationRole.OPERATOR]

# 默认从第一页查询
DEFAULT_PAGE = 1

# 查询用户组成员，全量查询
FETCH_USER_GROUP_MEMBERS_LIMIT = 10000

# 查询开发者中心分级管理员列表，全量查询
LIST_GRADE_MANAGERS_LIMIT = 15000


class ResourceType(str, StructuredEnum):
    """
    iam 上注册的资源类型
    """

    Application = 'application'
    # 蓝鲸监控：空间
    BkMonitorSpace = 'space'
    # 蓝鲸监控：APM 应用
    BkMonitorApm = 'apm_application'
    # 蓝鲸监控：仪表盘
    BkMonitorDashBoard = 'grafana_dashboard'
    # 蓝鲸日志：索引集
    BkLogIndices = 'indices'
    # 蓝鲸日志：采集项
    BkLogCollection = 'collection'
    # 蓝鲸日志：ES源
    BkLogEsSource = 'es_source'


class IAMErrorCodes(int, StructuredEnum):
    """
    iam api 返回错误码
    https://bk.tencent.com/docs/document/7.0/236/39801
    """

    # 资源冲突
    CONFLICT = 1902409


# 蓝鲸监控的在权限中心注册的系统 ID
BK_MONITOR_SYSTEM_ID = 'bk_monitorv3'
# 蓝鲸日志平台在权限中心注册的系统 ID
BK_LOG_SYSTEM_ID = 'bk_log_search'

# 蓝鲸应用在监控平台的最小化权限列表
APP_MINI_ACTIONS_IN_BK_MONITOR = {
    ResourceType.BkMonitorSpace: [
        'view_business_v2',
        'explore_metric_v2',
        'view_event_v2',
        'manage_event_v2',
        'view_notify_team_v2',
        'manage_notify_team_v2',
        'view_rule_v2',
        'manage_rule_v2',
        'view_downtime_v2',
        'manage_downtime_v2',
        'view_custom_metric_v2',
        'manage_custom_metric_v2',
        'view_custom_event_v2',
        'manage_custom_event_v2',
        'new_dashboard',
        'manage_datasource_v2',
        'export_config_v2',
        'import_config_v2',
    ],
    ResourceType.BkMonitorApm: [
        'view_apm_application_v2',
        'manage_apm_application_v2',
        'edit_single_dashboard',
    ],
    ResourceType.BkMonitorDashBoard: [
        'view_single_dashboard',
    ],
}

# 蓝鲸应用在日志平台的最小化权限列表
# 日志平台给空间相关的 resource_system 为监控，其他的为日志
APP_MINI_ACTIONS_IN_BK_LOG = {
    ResourceType.BkMonitorSpace: {
        'resource_system': BK_MONITOR_SYSTEM_ID,
        'actions': [
            'view_business_v2',
            'create_collection_v2',
            'create_es_source_v2',
            'create_indices_v2',
            'new_dashboard',
            'manage_extract_config_v2',
        ],
    },
    ResourceType.BkMonitorDashBoard: ['view_single_dashboard', 'edit_single_dashboard'],
    ResourceType.BkLogIndices: {
        'resource_system': BK_LOG_SYSTEM_ID,
        'actions': ['manage_indices_v2', 'search_log_v2'],
    },
    ResourceType.BkLogCollection: {
        'resource_system': BK_LOG_SYSTEM_ID,
        'actions': ['view_collection_v2', 'manage_collection_v2'],
    },
    ResourceType.BkLogEsSource: {
        'resource_system': BK_LOG_SYSTEM_ID,
        'actions': [
            'manage_es_source_v2',
        ],
    },
}


# 由于权限中心的用户组授权为异步行为，即创建用户组，添加用户，对组授权后需要等待一段时间（10-20秒左右）才能鉴权
# 因此需要在应用创建后的一定的时间内，对创建者（拥有应用最高权限）的操作进行权限豁免以保证功能可正常使用
PERM_EXEMPT_TIME_FOR_OWNER_AFTER_CREATE_APP = 5 * 60
