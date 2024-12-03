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
from datetime import datetime

from paasng.infras.oauth2.api import BkAppSecret


class StubBkOauthClient:
    """bkAuth 提供的 API（仅供单元测试使用）"""

    def create_client(self, bk_app_code: str): ...

    def create_app_secret(self, bk_app_code: str): ...

    def del_app_secret(self, bk_app_code: str, bk_app_secret_id: int): ...

    def toggle_app_secret(self, bk_app_code: str, bk_app_secret_id: int, enabled: bool): ...

    def get_app_secret_list(self, bk_app_code: str): ...

    def get_default_app_secret(self, bk_app_code: str):
        return BkAppSecret(
            id=1,
            bk_app_code=bk_app_code,
            bk_app_secret="xxxxxxx",
            enabled=True,
            created_at=datetime.strptime("2021-10-21T07:56:16Z", "%Y-%m-%dT%H:%M:%SZ"),
        )

    def get_secret_by_id(self, bk_app_code: str, bk_app_secret_id: int): ...
