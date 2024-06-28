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

from typing import Any, ClassVar

from paasng.utils.error_codes import error_codes


class BaseComponent:
    host: ClassVar[str] = ""
    system_name: ClassVar[str] = ""

    # TODO：可使用 typing_extensions.Protocol 为 http_func 定义约束
    def _call_api(self, http_func, path: str, **kwargs) -> Any:
        url = self._urljoin(self.host, path)
        http_ok, resp_data = http_func(url, **kwargs)

        if not (http_ok and resp_data):
            raise error_codes.REMOTE_REQUEST_ERROR.format(f"request {self.system_name} api error")

        if resp_data["code"] != 0:
            raise error_codes.REMOTE_REQUEST_ERROR.format(resp_data["message"], replace=True)

        return resp_data

    def _urljoin(self, host: str, path: str) -> str:
        if path.startswith("/"):
            host = host.rstrip("/")
        return f"{host}{path}"
