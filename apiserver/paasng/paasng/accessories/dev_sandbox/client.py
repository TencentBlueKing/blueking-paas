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
from typing import Dict, List

import requests
from django.utils.translation import gettext_lazy as _
from rest_framework import status

from paas_wl.bk_app.dev_sandbox.controller import DevSandboxWithCodeEditorController
from paasng.accessories.dev_sandbox.config_var import CONTAINER_TOKEN_ENV
from paasng.accessories.dev_sandbox.exceptions import CannotCommitToRepository, DevSandboxApiException
from paasng.accessories.dev_sandbox.models import DevSandbox
from paasng.platform.modules.models import Module


class DevSandboxApiClient:
    """沙箱开发 API 客户端（对应 cnb-builder-shim dev-entrypoint）"""

    def __init__(self, module: Module, dev_sandbox: DevSandbox, operator: str):
        self.module = module
        self.dev_sandbox = dev_sandbox
        self.operator = operator

        self.controller = DevSandboxWithCodeEditorController(
            app=module.application,
            module_name=module.name,
            dev_sandbox_code=self.dev_sandbox.code,
            owner=operator,
        )
        self.dev_sandbox_detail = self.controller.get_detail()

    def fetch_diffs(self) -> List[Dict]:
        """从沙箱获取代码变更文件"""
        # FIXME（沙箱重构）
        #  1. 这里的 devserver_url 其实只是个 host + prefix，没带 scheme 还以 / 结尾
        #  2. token 不应该从环境变量获取，建议重构时候加密存入 DevSandbox 表
        resp = requests.get(
            f"http://{self.dev_sandbox_detail.urls.devserver_url}codes/diffs",
            headers={"Authorization": f"Bearer {self.dev_sandbox_detail.dev_sandbox_env_vars[CONTAINER_TOKEN_ENV]}"},
            params={"content": "true"},
        )
        if resp.status_code != status.HTTP_200_OK:
            raise DevSandboxApiException(resp.text)

        resp_data = resp.json()
        if not resp_data["total"]:
            raise CannotCommitToRepository(_("没有可提交的代码变更"))

        return resp_data["files"]

    def commit(self, commit_msg: str) -> None:
        """在沙箱本地执行一次 commit"""
        # FIXME（沙箱重构）同上
        resp = requests.get(
            f"http://{self.dev_sandbox_detail.urls.devserver_url}codes/commit",
            headers={"Authorization": f"Bearer {self.dev_sandbox_detail.dev_sandbox_env_vars[CONTAINER_TOKEN_ENV]}"},
            params={"message": commit_msg},
        )
        if resp.status_code != status.HTTP_200_OK:
            raise DevSandboxApiException(resp.text)
