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


class LogQueryError(Exception):
    def __init__(self, message):
        super().__init__()
        self.message = message


class UnknownEngineAppNameError(Exception):
    def __init__(self, message):
        super().__init__()
        self.message = message


class LogLineInfoBrokenError(Exception):
    """日志行关键信息缺失异常"""

    def __init__(self, lacking_key: str):
        self.message = f"log line lacking key info: {lacking_key}"
        super().__init__(self.message)


class NoIndexError(Exception):
    """无可用 index"""


class BkLogGatewayServiceError(Exception):
    """This error indicates that there's something wrong when operating bk_log's
    API Gateway resource. It's a wrapper class of API SDK's original exceptions
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class BkLogApiError(BkLogGatewayServiceError):
    """When calling the bk_log api, bk_log returns an error message,
    which needs to be captured and displayed to the user on the page
    """


class TenantLogConfigNotFoundError(Exception):
    """该租户日志配置不存在"""

    def __init__(self, tenant_id: str):
        self.message = f"TenantLogConfig not found for tenant_id: {tenant_id}"
        super().__init__(self.message)


class SharedBkBizIdNotConfiguredError(Exception):
    """租户未配置平台级共享采集项所属的 CMDB 业务 ID"""

    def __init__(self, tenant_id: str):
        self.message = (
            f"shared_bk_biz_id is not configured for tenant_id: {tenant_id}, "
            "please set it via `python manage.py create_tenant_log_config --update --shared-bk-biz-id <biz_id>`"
        )
        super().__init__(self.message)
