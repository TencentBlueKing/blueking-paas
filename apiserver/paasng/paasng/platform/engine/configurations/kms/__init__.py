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

"""使用蓝鲸 KMS 托管敏感环境变量"""

from paasng.platform.engine.configurations.env_var.encryption import is_kms_injection_enabled

from .injection import (
    add_kms_secret_mount,
    collect_kms_managed_keys_by_env,
    ensure_kms_injection_supported,
    ensure_kms_mount_available,
    split_kms_managed_env_vars,
    strip_kms_managed_env_vars,
)
from .provisioner import provision_kms_secret

__all__ = [
    "add_kms_secret_mount",
    "collect_kms_managed_keys_by_env",
    "ensure_kms_injection_supported",
    "ensure_kms_mount_available",
    "is_kms_injection_enabled",
    "provision_kms_secret",
    "split_kms_managed_env_vars",
    "strip_kms_managed_env_vars",
]
