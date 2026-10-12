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

from paasng.core.tenant.constants import API_HERDER_TENANT_ID

KMS_USERNAME_HEADER = "X-Bk-Username"
KMS_TENANT_ID_HEADER = API_HERDER_TENANT_ID

CRYPTO_CATEGORY_NORMAL = "normal"
CREDENTIAL_TYPE_SECRET = "secret"
SCOPE_TYPE_SCOPE = "scope"
SUPPORTED_SCOPE_TYPES = frozenset({"biz", "biz_set", "scope"})

# 当前只支持 RSA 包装对称密钥、AES-128-CBC 加密明文的组合
SUPPORTED_CRYPTO_SUITE = ("RSA", "AES", "CBC")
AES_KEY_BYTES = 16
AES_BLOCK_BYTES = 16

ERROR_CODE_RESOURCE_NOT_FOUND = 1034003

# 长度限制（字符数）
PLAINTEXT_MAX_CHARS = 65536
CREDENTIAL_NAME_MAX_CHARS = 128
DESCRIPTION_MAX_CHARS = 2048
ANNOTATION_MAX_CHARS = 10240
SERVICE_ACCOUNT_NAME_MAX_CHARS = 253
SERVICE_ACCOUNT_LIST_MAX_ITEMS = 1024

# Kubernetes Secret 的数据上限（字节），信封必须小于该值
K8S_SECRET_MAX_BYTES = 1024 * 1024
K8S_NAME_MAX_CHARS = 253

# 凭证在 OpenBao 中的字段名，以及 ESO 同步到 Secret 后的字段名（应用 SDK 按后者读取挂载文件）
OPENBAO_ENVELOPE_PROPERTY = "envelope"
OPENBAO_PRIVATE_KEY_PROPERTY = "private_key"
SECRET_KEY_ENVELOPE = "envelope"
SECRET_KEY_PRIVATE_KEY = "privateKey"

# 访问 OpenBao 的 mTLS 客户端证书 Secret 中的字段名
MTLS_SECRET_KEY_CA = "ca.crt"
MTLS_SECRET_KEY_CERT = "tls.crt"
MTLS_SECRET_KEY_PRIVATE_KEY = "tls.key"

# 卷名必须是 DNS label（最长 63 字符），因此使用固定值，而不是包含租户和凭证名的资源名
KMS_SECRET_MOUNT_DIR = "/etc/kms"
KMS_SECRET_VOLUME_NAME = "kms-secret"

# 明文 payload 的格式版本，应用端解析时据此校验
FROZEN_PAYLOAD_SCHEMA_VERSION = 1
