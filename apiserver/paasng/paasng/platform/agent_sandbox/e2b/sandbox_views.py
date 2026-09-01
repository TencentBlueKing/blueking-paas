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

"""e2b 控制面协议端点。

这些端点由 e2b SDK 直接调用，路径与请求响应形态都由 e2b 协议规定

兼容层的异常不在这里捕获，由 ``base_views.e2b_exception_handler`` 统一映射，
避免每个端点各写一遍 try/except 而漏掉分支。
"""

import logging

from rest_framework import status
from rest_framework.response import Response

from . import sandboxes
from .base_views import E2BProtocolViewSet
from .serializers import E2BSandboxCreateInputSLZ, E2BSandboxTimeoutInputSLZ

logger = logging.getLogger(__name__)


class E2BSandboxViewSet(E2BProtocolViewSet):
    """沙箱生命周期的 e2b 兼容端点。"""

    def create(self, request):
        """创建沙箱"""
        slz = E2BSandboxCreateInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        resp = sandboxes.create_sandbox(self.application, dict(request.data))
        return Response(resp, status=status.HTTP_201_CREATED)

    def list(self, request):
        """列出本应用名下存活的沙箱"""
        return Response(sandboxes.list_sandboxes(self.application))

    def retrieve(self, request, sandbox_id):
        """查询沙箱详情"""
        return Response(sandboxes.get_sandbox(self.application, sandbox_id))

    def destroy(self, request, sandbox_id):
        """销毁沙箱，重复调用幂等。"""
        sandboxes.kill_sandbox(self.application, sandbox_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def set_timeout(self, request, sandbox_id):
        """重设沙箱存活时长"""
        slz = E2BSandboxTimeoutInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        sandboxes.set_sandbox_timeout(self.application, sandbox_id, slz.validated_data["timeout"])
        return Response(status=status.HTTP_204_NO_CONTENT)
