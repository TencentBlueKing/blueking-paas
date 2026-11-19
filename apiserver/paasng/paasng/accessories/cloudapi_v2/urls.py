# -*- coding: utf-8 -*-
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

from django.urls import include, path

from paasng.accessories.cloudapi_v2.apigateway import urls as apigateway_urls
from paasng.accessories.cloudapi_v2.mcp_servers import urls as mcp_server_urls

urlpatterns = [
    # MCP Server 相关
    path("api/cloudapi-v2/", include("paasng.accessories.cloudapi_v2.mcp_servers.urls")),
    # 网关 API & ESB 组件 API 相关
    path("api/cloudapi-v2/", include("paasng.accessories.cloudapi_v2.apigateway.urls")),
]

# System APIs: 给固定的系统调用
# 应用态接口的路径以 sys/api/ 开头，与用户态 api/ 前缀不冲突，因此直接挂载、不叠加 cloudapi-v2 前缀
urlpatterns += apigateway_urls.sys_urlpatterns
urlpatterns += mcp_server_urls.sys_urlpatterns
