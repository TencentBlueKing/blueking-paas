# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

"""蓝鲸开发者中心：应用态系统 API 客户端和前端页面链接。"""

from app_spark_api.infras.bk_paas.client import BKAPI_AUTHORIZATION_HEADER, BkPaaSClient, build_gateway_base_url
from app_spark_api.infras.bk_paas.console import ConsoleLinks, build_console_links, build_deployment_detail_url
from app_spark_api.infras.bk_paas.entities import (
    UNIQUE_APP_FIELD_CODE,
    AppBasicInfoValidation,
    AppFieldError,
    CreatedApp,
    Deployment,
    DeploymentResult,
    DeploymentStatus,
)
from app_spark_api.infras.bk_paas.exceptions import (
    BkPaaSApiError,
    BkPaaSConfigurationError,
    BkPaaSError,
    BkPaaSUnavailableError,
)

__all__ = [
    "BKAPI_AUTHORIZATION_HEADER",
    "UNIQUE_APP_FIELD_CODE",
    "AppBasicInfoValidation",
    "AppFieldError",
    "BkPaaSApiError",
    "BkPaaSClient",
    "BkPaaSConfigurationError",
    "BkPaaSError",
    "BkPaaSUnavailableError",
    "ConsoleLinks",
    "CreatedApp",
    "Deployment",
    "DeploymentResult",
    "DeploymentStatus",
    "build_console_links",
    "build_deployment_detail_url",
    "build_gateway_base_url",
]
