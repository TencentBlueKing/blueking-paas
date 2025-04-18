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

from typing import Optional

from blue_krill.models.fields import EncryptField
from django.db import models, transaction
from jsonfield import JSONField
from paas_service.models import UuidAuditedModel

from .constants import (
    ClusterAnnotationKey,
    ClusterTokenType,
    ClusterType,
)


class Cluster(UuidAuditedModel):
    """应用集群"""

    name = models.CharField(help_text="集群名称", max_length=32, unique=True)
    type = models.CharField(max_length=32, help_text="集群类型", default=ClusterType.NORMAL)
    description = models.TextField(help_text="集群描述", blank=True)

    annotations = JSONField(help_text="集群元数据，如 BCS 项目，集群，业务信息等", default=dict, blank=True)

    # 认证方式 A
    ca_data = EncryptField(help_text="证书认证机构（CA）", null=True, blank=True)
    cert_data = EncryptField(help_text="客户端证书", null=True, blank=True)
    key_data = EncryptField(help_text="客户端密钥", null=True, blank=True)
    # 认证方式 B
    token_type = models.IntegerField(help_text="Token 类型", default=ClusterTokenType.SERVICE_ACCOUNT)
    token_value = EncryptField(help_text="Token 值", null=True, blank=True)
    # 可选值：True, False, None 或 hostname 字符串（如 kubernetes）
    # https://github.com/TencentBlueKing/blueking-paas/pull/1845#discussion_r1898229643
    assert_hostname = models.JSONField(help_text="TLS 验证主机名", default=None, null=True, blank=True)

    class Meta:
        verbose_name_plural = verbose_name = "集群"

    def __str__(self):
        return f"{self.__class__.__name__}(name={self.name}"

    @property
    def bcs_project_id(self) -> Optional[str]:
        """集群在 bcs 中注册的集群所属的项目 ID"""
        return self.annotations.get(ClusterAnnotationKey.BCS_PROJECT_ID, None)

    @property
    def bcs_cluster_id(self) -> Optional[str]:
        """集群在 bcs 中注册的集群 ID"""
        return self.annotations.get(ClusterAnnotationKey.BCS_CLUSTER_ID, None)

    @property
    def bk_biz_id(self) -> Optional[str]:
        """bcs 集群所在项目在 bkcc 中的业务 ID"""

        # 如果不是 bcs 集群，则 bkcc 业务 ID 不会生效
        if not self.bcs_cluster_id:
            return None

        return self.annotations.get(ClusterAnnotationKey.BK_BIZ_ID, None)


class APIServer(UuidAuditedModel):
    cluster = models.ForeignKey(to=Cluster, related_name="api_servers", on_delete=models.CASCADE)
    host = models.CharField(max_length=255, help_text="API Server 的后端地址")

    class Meta:
        unique_together = ("cluster", "host")
        verbose_name_plural = verbose_name = "API Server"


class TencentCLBEndpoint(UuidAuditedModel):
    """CLB 端点"""

    name = models.CharField(max_length=255, help_text="CLB 名称")
    cluster = models.ForeignKey(to=Cluster, related_name="clb_ports", on_delete=models.CASCADE)
    clb_id = models.CharField(max_length=255, help_text="CLB ID")
    vip = models.GenericIPAddressField(help_text="CLB VIP 地址")
    port = models.IntegerField(help_text="CLB 端口")
    is_allocated = models.BooleanField(default=False, help_text="是否已被分配")

    class Meta:
        unique_together = ("cluster", "vip", "port")
        verbose_name_plural = verbose_name = "腾讯云 CLB 端点"

    def acquire(self):
        self.is_allocated = True
        self.save(update_fields=["is_allocated"])

    def release(self):
        self.is_allocated = False
        self.save(update_fields=["is_allocated"])

    @classmethod
    def acquire_clb_endpoint_by_cluster_name(cls, cluster_name: str) -> "TencentCLBEndpoint":
        """
        线程安全地获取并分配一个可用的 CLB 端点
        """
        with transaction.atomic():
            try:
                # 使用 select_for_update 锁定符合条件的记录，防止并发修改
                clb_endpoint = (
                    cls.objects.select_for_update().filter(cluster__name=cluster_name, is_allocated=False).first()
                )
            except Exception as e:
                raise ValueError(f"Failed to acquire CLB endpoint: {e}")
            else:
                if not clb_endpoint:
                    raise ValueError(f"No available CLB endpoints for cluster {cluster_name}.")

                clb_endpoint.acquire()
                return clb_endpoint

    @classmethod
    def release_clb_endpoint(cls, cluster_name: str, vip: str, port: int) -> None:
        """
        根据集群名称、VIP 和端口释放 CLB 端点。
        """
        try:
            clb_endpoint = cls.objects.get(
                cluster__name=cluster_name,
                vip=vip,
                port=port,
                is_allocated=True,
            )
            clb_endpoint.release()
        except cls.DoesNotExist:
            raise ValueError(f"CLB Endpoint {vip}:{port} not found or not allocated.")
        except Exception as e:
            raise ValueError(f"Failed to release CLB endpoint: {e}")
