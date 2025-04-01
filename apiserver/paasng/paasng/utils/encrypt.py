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

"""
classes & methods in this file should be used in new module
remaining for old data
"""

from typing import AnyStr

from blue_krill.encrypt.legacy import legacy_decrypt, legacy_encrypt
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class EncryptHandler:
    """密码加解密类"""

    def __init__(self):
        _secret_key = getattr(settings, "PAAS_LEGACY_DB_ENCRYPT_KEY", None)
        if not _secret_key:
            raise ImproperlyConfigured("`PAAS_LEGACY_DB_ENCRYPT_KEY` must be configured to use EncryptHandler")

        self.secret_key: str = _secret_key

    def encrypt(self, text: AnyStr) -> str:
        """加密数据

        :param text: app_secret 或者 db password 或者svn password
        """
        return legacy_encrypt(text, self.secret_key)

    def decrypt(self, text: AnyStr) -> str:
        """解密数据"""
        return legacy_decrypt(text, self.secret_key)
