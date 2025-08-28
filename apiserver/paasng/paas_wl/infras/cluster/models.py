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

import logging
from typing import Any, Dict, List, Optional

from blue_krill.models.fields import EncryptField
from django.db import models, transaction
from jsonfield import JSONField

from paas_wl.infras.cluster.constants import (
    ClusterAnnotationKey,
    ClusterFeatureFlag,
    ClusterTokenType,
    ClusterType,
)
from paas_wl.infras.cluster.entities import AllocationPolicy, AllocationPrecedencePolicy, IngressConfig
from paas_wl.infras.cluster.validators import validate_ingress_config
from paas_wl.utils.models import UuidAuditedModel
from paasng.core.tenant.fields import tenant_id_field_factory
from paasng.platform.modules.constants import ExposedURLType
from paasng.utils.models import make_json_field

logger = logging.getLogger(__name__)


class ClusterManager(models.Manager):
    @transaction.atomic(using="workloads")
    def register_cluster(
        self,
        name: str,
        type: str = ClusterType.NORMAL,
        description: Optional[str] = None,
        exposed_url_type: int = ExposedURLType.SUBPATH.value,
        ingress_config: Optional[Dict] = None,
        annotations: Optional[Dict] = None,
        ca_data: Optional[str] = None,
        cert_data: Optional[str] = None,
        key_data: Optional[str] = None,
        token_type: Optional[ClusterTokenType] = None,
        token_value: Optional[str] = None,
        default_node_selector: Optional[Dict] = None,
        default_tolerations: Optional[List] = None,
        feature_flags: Optional[Dict] = None,
        pk: Optional[str] = None,
        **kwargs,
    ) -> "Cluster":
        """Register a cluster to db, work Like update_or_create, but will validate some-attr

        Auth type: client-side cert
        ---------------------------

        :param cert_data: client cert data
        :param key_data: client key data

        Auth type: Bearer token
        -----------------------

        :param token_type: token type, use `SERVICE_ACCOUNT` by default
        :param token_value: value of token
        """
        # FIXME（多租户）多租户初始化时，需要重新整理这里的逻辑

        validate_ingress_config(ingress_config)

        defaults: Dict[str, Any] = {
            "type": type,
            "description": description,
            "exposed_url_type": exposed_url_type,
            "ingress_config": ingress_config,
            "annotations": annotations,
            "ca_data": ca_data,
            "cert_data": cert_data,
            "key_data": key_data,
            "default_node_selector": default_node_selector,
            "default_tolerations": default_tolerations,
            "feature_flags": feature_flags,
        }
        if token_value:
            _token_type = token_type or ClusterTokenType.SERVICE_ACCOUNT
            defaults.update({"token_value": token_value, "token_type": _token_type})

        # We use `None` to mark this fields is unset, so we should pop it from defaults.
        defaults = {k: v for k, v in defaults.items() if v is not None}

        if pk:
            cluster, _ = self.update_or_create(pk=pk, name=name, defaults=defaults)
        else:
            cluster, _ = self.update_or_create(name=name, defaults=defaults)
        return cluster


IngressConfigField = make_json_field(cls_name="IngressConfigField", py_model=IngressConfig)


class Cluster(UuidAuditedModel):
    """应用集群"""

    available_tenant_ids = models.JSONField(help_text="可用的租户 ID 列表", default=list)

    name = models.CharField(help_text="集群名称", max_length=32, unique=True)
    type = models.CharField(max_length=32, help_text="集群类型", default=ClusterType.NORMAL)
    description = models.TextField(help_text="集群描述", blank=True)

    exposed_url_type = models.IntegerField(help_text="应用的访问地址类型", default=ExposedURLType.SUBPATH.value)
    ingress_config: IngressConfig = IngressConfigField(help_text="ingress 配置")
    annotations = JSONField(help_text="集群元数据，如 BCS 项目，集群，业务信息等", default=dict)

    # 认证方式 A
    ca_data = EncryptField(help_text="证书认证机构（CA）", null=True)
    cert_data = EncryptField(help_text="客户端证书", null=True)
    key_data = EncryptField(help_text="客户端密钥", null=True)
    # 认证方式 B
    token_type = models.IntegerField(help_text="Token 类型", default=ClusterTokenType.SERVICE_ACCOUNT)
    token_value = EncryptField(help_text="Token 值", null=True)
    # 可选值：True, False, None 或 hostname 字符串（如 kubernetes）
    # https://github.com/TencentBlueKing/blueking-paas/pull/1845#discussion_r1898229643
    assert_hostname = models.JSONField(help_text="TLS 验证主机名", default=None, null=True)

    # App 默认配置
    default_node_selector = JSONField(help_text="部署到本集群的应用默认节点选择器（node_selector）", default=dict)
    default_tolerations = JSONField(help_text="部署到本集群的应用默认容忍度（tolerations）", default=list)
    container_log_dir = models.CharField(
        help_text="容器日志目录", max_length=255, default="/var/lib/docker/containers"
    )

    # 集群组件
    component_preferred_namespace = models.CharField(
        help_text="集群组件优先部署的命名空间", max_length=64, default="blueking"
    )
    component_image_registry = models.CharField(
        help_text="集群组件镜像仓库地址", max_length=255, default="hub.bktencent.com"
    )
    # 集群特性，具体枚举值 -> ClusterFeatureFlag
    feature_flags = JSONField(help_text="集群特性集", default=dict)

    tenant_id = tenant_id_field_factory()

    objects = ClusterManager()

    def __str__(self):
        return f"{self.__class__.__name__}(name={self.name}, tenant={self.tenant_id})"

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

    def has_feature_flag(self, ff: ClusterFeatureFlag) -> bool:
        """检查当前集群是否支持某个特性"""
        default_flags = ClusterFeatureFlag.get_default_flags()
        return self.feature_flags.get(ff, default_flags[ff])


class APIServer(UuidAuditedModel):
    cluster = models.ForeignKey(to=Cluster, related_name="api_servers", on_delete=models.CASCADE)
    host = models.CharField(max_length=255, help_text="API Server 的后端地址")

    tenant_id = tenant_id_field_factory()

    class Meta:
        unique_together = ("cluster", "host")

    def __str__(self):
        return f"{self.__class__.__name__}(cluster={self.cluster.name}, host={self.host}"


class ClusterComponent(UuidAuditedModel):
    """集群组件（由 Helm Chart 进行安装）"""

    cluster = models.ForeignKey(to=Cluster, related_name="components", on_delete=models.CASCADE)
    repository = models.CharField(max_length=64, help_text="Helm 组件仓库", default="public-repo")
    name = models.CharField(max_length=64, help_text="组件名称")
    required = models.BooleanField(help_text="是否为必要组件")

    tenant_id = tenant_id_field_factory()

    class Meta:
        unique_together = ("cluster", "name")

    def __str__(self):
        return (
            f"{self.__class__.__name__}(cluster={self.cluster.name}, "
            + f"repository={self.repository}, name={self.name}, required={self.required})"
        )


AllocationPolicyField = make_json_field("AllocationPolicyField", AllocationPolicy)

AllocationPrecedencePoliciesField = make_json_field(
    "AllocationPrecedencePoliciesField", List[AllocationPrecedencePolicy]
)


class ClusterAllocationPolicy(UuidAuditedModel):
    """集群分配策略"""

    # 枚举值 -> ClusterAllocationPolicyType
    type = models.CharField(max_length=32, help_text="分配策略类型")
    allocation_policy: AllocationPolicy | None = AllocationPolicyField(
        help_text="统一分配策略", default=None, null=True
    )
    allocation_precedence_policies: List[AllocationPrecedencePolicy] = AllocationPrecedencePoliciesField(
        help_text="规则分配优先策略", default=list
    )

    tenant_id = tenant_id_field_factory(unique=True)


class ClusterElasticSearchConfig(UuidAuditedModel):
    """集群 ES 配置"""

    cluster = models.OneToOneField(Cluster, related_name="elastic_search_config", on_delete=models.CASCADE)
    scheme = models.CharField(help_text="ES 集群协议", max_length=12)
    host = models.CharField(help_text="ES 集群地址", max_length=128)
    port = models.IntegerField(help_text="ES 集群端口")
    username = models.CharField(help_text="ES 集群用户名", max_length=64)
    password = EncryptField(help_text="ES 集群密码")

    # TLS 配置信息
    verify_certs = models.BooleanField(help_text="是否验证 TLS 证书", default=False)
    ca_certs = models.TextField(help_text="ES 集群 CA 证书", null=True)
    client_cert = models.TextField(help_text="ES 集群客户端证书", null=True)
    client_key = models.TextField(help_text="ES 集群客户端密钥", null=True)

    tenant_id = tenant_id_field_factory()


class ClusterAppImageRegistry(UuidAuditedModel):
    """
    集群应用镜像仓库配置

    默认租户 & 运营租户的集群，均可使用 settings 中配置的默认应用镜像仓库
    但是非运营租户，或者托管到默认租户 / 运营租户的集群，则应该使用自定义应用镜像仓库
    其目的是避免下发到集群中的 imagePullSecret 中包含默认租户的凭证继而导致泄露
    """

    cluster = models.OneToOneField(Cluster, related_name="app_image_registry", on_delete=models.CASCADE)
    host = models.CharField(help_text="镜像仓库地址", max_length=256)
    skip_tls_verify = models.BooleanField(help_text="是否跳过 TLS 证书验证", default=False)
    namespace = models.CharField(help_text="镜像仓库命名空间", max_length=128)
    username = models.CharField(help_text="镜像仓库用户名", max_length=64)
    password = EncryptField(help_text="镜像仓库密码")

    tenant_id = tenant_id_field_factory()
