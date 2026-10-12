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

import uuid

from django.db import models

from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.platform.engine.constants import KMSCleanupStatus, KMSConfigVersionStatus
from paasng.utils.models import AuditedModel, Char32UUIDField


class KMSConfigVersion(AuditedModel):
    """敏感变量的 KMS 配置版本

    每次需要 KMS 托管的部署新建一个版本，不复用。记录只保存标量引用，不设外键：应用、模块或部署删除后，
    记录仍然保留，供清理任务按记录回收远端资源。

    `envelope` 是 KMS 信封密文，PaaS 无法解密；明文、私钥和原始请求都不写入本表。
    """

    id = Char32UUIDField("UUID", default=uuid.uuid4, primary_key=True, editable=False, auto_created=True, unique=True)
    tenant_id = tenant_id_field_factory()

    # 归属信息（标量引用，不使用外键）
    app_code = models.CharField(max_length=64)
    module_name = models.CharField(max_length=64)
    env_name = models.CharField(max_length=16)
    module_environment_id = models.CharField(max_length=32)

    status = models.CharField(
        "准备状态",
        choices=KMSConfigVersionStatus.get_choices(),
        max_length=32,
        default=KMSConfigVersionStatus.PENDING.value,
    )
    # 冻结输入：重试时原样提交同一份信封，不重新读取用户后来修改的变量
    envelope = models.TextField("KMS 信封（密文）")

    # KMS 侧资源
    kms_scope_id = models.IntegerField("KMS scope ID", null=True)
    credential_id = models.BigIntegerField("KMS 凭证 ID", null=True)
    credential_name = models.CharField(max_length=128)
    openbao_key = models.CharField("OpenBao 路径", max_length=255)
    kms_role = models.CharField(max_length=255)

    # Kubernetes 侧资源
    cluster_name = models.CharField(max_length=64)
    namespace = models.CharField(max_length=63)
    service_account_name = models.CharField(max_length=253)
    cluster_secret_store_name = models.CharField("ClusterSecretStore 名称", max_length=253)
    resource_name = models.CharField("ExternalSecret 与 Secret 名称", max_length=253)
    cluster_secret_store_uid = models.CharField(max_length=64, blank=True, default="")
    external_secret_uid = models.CharField(max_length=64, blank=True, default="")
    secret_uid = models.CharField(max_length=64, blank=True, default="")

    cleanup_status = models.CharField(
        "清理状态",
        choices=KMSCleanupStatus.get_choices(),
        max_length=32,
        default=KMSCleanupStatus.NOT_REQUESTED.value,
        db_index=True,
    )
    # 只记录安全的错误分类，不记录响应正文或 Secret 内容
    error_reason = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        indexes = [models.Index(fields=["app_code", "module_name", "env_name"])]

    def __str__(self):
        return f"{self.app_code}/{self.module_name}/{self.env_name}/{self.id}"
