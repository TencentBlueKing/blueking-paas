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

"""应用态 (系统 API) 视图

这些接口注册在 `sys/api/` 路径下, 仅供 AIDEV / AppSpark 等固定的系统调用, 鉴权依赖 sysapi_client.
"""

from typing import List

from paasng.infras.sysapi_client.constants import ClientAction
from paasng.infras.sysapi_client.roles import sysapi_client_perm_class

from .logs import StructuredLogAPIView


class SysStructuredLogAPIView(StructuredLogAPIView):
    permission_classes: List = [sysapi_client_perm_class(ClientAction.READ_APPLICATIONS)]

    def query_logs(self, request, code, module_name, environment):
        return super().query_logs(request, code, module_name, environment)
