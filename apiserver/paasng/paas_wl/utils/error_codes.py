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
    PROCESS_OPERATE_FAILED = ErrorCode(_("进程操作失败"))

    # New error codes for end-user views
    ERROR_ACQUIRING_EGRESS_GATEWAY_INFO = ErrorCode(_("无法获取出口 IP 信息"))
    ERROR_RECYCLING_EGRESS_GATEWAY_INFO = ErrorCode(_("无法清除出口 IP 信息"))
    # RegionClusterState end

    # New error codes for end-user views
    ERROR_UPDATING_PROC_SERVICE = ErrorCode(_("无法更新进程服务"))
    ERROR_UPDATING_PROC_INGRESS = ErrorCode(_("无法更新主入口"))

    # Process related codes
    CANNOT_OPERATE_PROCESS = ErrorCode(_("操作进程失败"))
    PROCESS_OPERATION_TOO_OFTEN = ErrorCode(_("进程操作过于频繁，请稍后再试"))
    PROCESS_INSTANCE_NOT_FOUND = ErrorCode(_("无法找到进程实例"))

    # Custom Domain Start
    DELETE_CUSTOM_DOMAIN_FAILED = ErrorCode(_("删除独立域名失败"))
    CREATE_CUSTOM_DOMAIN_FAILED = ErrorCode(_("创建独立域名失败"))
    UPDATE_CUSTOM_DOMAIN_FAILED = ErrorCode(_("修改独立域名失败"))

    # Edition Start
    EDITION_NOT_SUPPORT = ErrorCode(_("该功能当前版本不支持"))

    # cnative
    BKAPP_NOT_SET = ErrorCode(_("未设置部署信息"))
    INVALID_MRES = ErrorCode(_("The bkapp is invalid"))
    GET_DEPLOYMENT_FAILED = ErrorCode(_("Failed to find deployed version"))
    LIST_TAGS_FAILED = ErrorCode(_("Failed to list tag from image repository"))
    CREATE_VOLUME_MOUNT_FAILED = ErrorCode(_("Failed to create volume mount"))
    LIST_VOLUME_MOUNTS_FAILED = ErrorCode(_("Failed to list volume mount"))
    UPDATE_VOLUME_MOUNT_FAILED = ErrorCode(_("Failed to update volume mount"))
    LIST_VOLUME_SOURCES_FAILED = ErrorCode(_("Failed to list volume mount sources"))
    CREATE_VOLUME_SOURCE_FAILED = ErrorCode(_("Failed to create volume mount source"))

    # Credentials
    CREATE_CREDENTIALS_FAILED = ErrorCode(_("Failed to create credentials"))
    INVALID_CREDENTIALS = ErrorCode(_("Image credentials is invalid"))
    DELETE_CREDENTIALS_FAILED = ErrorCode(_("Failed to delete credentials"))

    # 集群组件相关
    SWITCH_DEFAULT_CLUSTER_FAILED = ErrorCode(_("Failed to switch default cluster"))
    CLUSTER_COMPONENT_NOT_EXIST = ErrorCode(_("Cluster component not exist"))

    # AI Agent 相关
    AI_AGENT_SERVICE_ERROR = ErrorCode(_("AI Agent service error"))


error_codes = ErrorCodes()
