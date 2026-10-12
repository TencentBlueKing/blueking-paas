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

"""KMS 凭证托管接入的常量，取值来源于 KMS 管理接口文档"""

from paasng.core.tenant.constants import API_HERDER_TENANT_ID

# 调用 KMS 管理接口时携带的请求头。bk-dev 直连使用这两个头，正式服务身份待运维确认
KMS_USERNAME_HEADER = "X-Bk-Username"
KMS_TENANT_ID_HEADER = API_HERDER_TENANT_ID

# 接口参数取值
CRYPTO_CATEGORY_NORMAL = "normal"
CREDENTIAL_TYPE_SECRET = "secret"
SCOPE_TYPE_SCOPE = "scope"
SUPPORTED_SCOPE_TYPES = frozenset({"biz", "biz_set", "scope"})

# 服务端下发的加密套件中，当前实现支持的组合：RSA 包装对称密钥，AES-128-CBC 加密明文
SUPPORTED_CRYPTO_SUITE = ("RSA", "AES", "CBC")
AES_KEY_BYTES = 16
AES_BLOCK_BYTES = 16
AES_BLOCK_BITS = 128

# 业务错误码：资源不存在
ERROR_CODE_RESOURCE_NOT_FOUND = 1034003

# 长度限制（字符数）。明文上限按解密后的字符数计算
PLAINTEXT_MAX_CHARS = 65536
CREDENTIAL_NAME_MAX_CHARS = 128
DESCRIPTION_MAX_CHARS = 2048
ANNOTATION_MAX_CHARS = 10240
SERVICE_ACCOUNT_NAME_MAX_CHARS = 253
SERVICE_ACCOUNT_LIST_MAX_ITEMS = 1024

# Kubernetes Secret 对象的数据上限（字节），信封的大小必须低于该值
K8S_SECRET_MAX_BYTES = 1024 * 1024
K8S_NAME_MAX_CHARS = 253

# OpenBao 中凭证的字段名（蓝鲸 KMS 约定），ESO 同步到 Kubernetes Secret 后使用下面的字段名
OPENBAO_ENVELOPE_PROPERTY = "envelope"
OPENBAO_PRIVATE_KEY_PROPERTY = "private_key"
SECRET_KEY_ENVELOPE = "envelope"
SECRET_KEY_PRIVATE_KEY = "privateKey"

# mTLS 客户端证书 Secret 中的字段名，与 bk-apigateway 的约定一致
MTLS_SECRET_KEY_CA = "ca.crt"
MTLS_SECRET_KEY_CERT = "tls.crt"
MTLS_SECRET_KEY_PRIVATE_KEY = "tls.key"

# 挂载目录与卷名。卷名必须是 DNS label（最长 63 字符），因此不使用包含租户和凭证名的资源名
KMS_SECRET_MOUNT_DIR = "/etc/kms"
KMS_SECRET_VOLUME_NAME = "kms-secret"

# 冻结明文的格式版本，应用端解析时据此校验
FROZEN_PAYLOAD_SCHEMA_VERSION = 1
