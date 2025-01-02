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
from paas_wl.infras.cluster.entities import AllocationRule, IngressConfig, ManualAllocationConfig
from paas_wl.infras.cluster.exceptions import (
    DuplicatedDefaultClusterError,
    NoDefaultClusterError,
    SwitchDefaultClusterError,
)
from paas_wl.infras.cluster.validators import validate_ingress_config
from paas_wl.utils.models import UuidAuditedModel
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from paasng.utils.models import make_json_field

logger = logging.getLogger(__name__)


class ClusterManager(models.Manager):
    @transaction.atomic(using="workloads")
    def register_cluster(
        self,
        region: str,
        name: str,
        type: str = ClusterType.NORMAL,
        is_default: bool = False,
        description: Optional[str] = None,
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
        default_cluster_qs = self.filter(region=region, is_default=True)

        if not default_cluster_qs.exists() and not is_default:
            raise NoDefaultClusterError("This region has not define a default cluster.")
        elif default_cluster_qs.filter(name=name).exists() and not is_default:
            raise SwitchDefaultClusterError(
                "Can't change default cluster by calling `register_cluster`, please use `switch_default_cluster`"
            )
        elif default_cluster_qs.exclude(name=name).exists() and is_default:
            raise DuplicatedDefaultClusterError("This region should have one and only one default cluster.")

        validate_ingress_config(ingress_config)

        defaults: Dict[str, Any] = {
            "type": type,
            "is_default": is_default,
            "description": description,
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
            cluster, _ = self.update_or_create(pk=pk, name=name, region=region, defaults=defaults)
        else:
            cluster, _ = self.update_or_create(name=name, region=region, defaults=defaults)
        return cluster

    @transaction.atomic(using="workloads")
    def switch_default_cluster(self, region: str, cluster_name: str) -> "Cluster":
        """Switch the default cluster to the cluster called `cluster_name`.

        :raise SwitchDefaultClusterException: if the cluster called `cluster_name` is already the default cluster.
        """
        try:
            prep_default_cluster = self.select_for_update().get(region=region, name=cluster_name)
            curr_default_cluster = self.select_for_update().get(region=region, is_default=True)
        except self.model.DoesNotExist:
            raise SwitchDefaultClusterError("Can't switch default cluster to a not-existed cluster.")

        if prep_default_cluster.name == curr_default_cluster.name:
            raise SwitchDefaultClusterError("The cluster is already the default cluster.")

        curr_default_cluster.is_default = False
        prep_default_cluster.is_default = True

        curr_default_cluster.save()
        prep_default_cluster.save()

        return prep_default_cluster


IngressConfigField = make_json_field(cls_name="IngressConfigField", py_model=IngressConfig)


class Cluster(UuidAuditedModel):
    """应用集群"""

    region = models.CharField(help_text="可用区域", max_length=32, db_index=True)
    tenant_id = models.CharField(help_text="所属租户", max_length=128, default=DEFAULT_TENANT_ID)
    available_tenant_ids = models.JSONField(help_text="可用的租户 ID 列表", default=list)

    name = models.CharField(help_text="集群名称", max_length=32, unique=True)
    type = models.CharField(max_length=32, help_text="集群类型", default=ClusterType.NORMAL)
    description = models.TextField(help_text="集群描述", blank=True)
    is_default = models.BooleanField(
        help_text="是否为默认集群（deprecated，后续由分配策略替代）", default=False, null=True
    )

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

    objects = ClusterManager()

    def __str__(self):
        return f"{self.__class__.__name__}(name={self.name}, tenant={self.tenant_id}, region={self.region})"

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
        default_flags = ClusterFeatureFlag.get_default_flags_by_cluster_type(
            cluster_type=ClusterType(self.type),
        )
        return self.feature_flags.get(ff, default_flags[ff])


class APIServer(UuidAuditedModel):
    cluster = models.ForeignKey(to=Cluster, related_name="api_servers", on_delete=models.CASCADE)
    host = models.CharField(max_length=255, help_text="API Server 的后端地址")

    class Meta:
        unique_together = ("cluster", "host")


ManualAllocationConfigField = make_json_field("ManualAllocationConfigField", ManualAllocationConfig)

AllocationRulesField = make_json_field("AllocationRulesField", List[AllocationRule])


class ClusterAllocationPolicy(UuidAuditedModel):
    """集群分配策略"""

    tenant_id = models.CharField(max_length=128, unique=True, help_text="所属租户")
    # 枚举值 -> ClusterAllocationPolicyType
    type = models.CharField(max_length=32, help_text="分配策略类型")
    manual_allocation_config: ManualAllocationConfig | None = ManualAllocationConfigField(
        help_text="手动分配配置", default=None
    )
    allocation_rules: List[AllocationRule] = AllocationRulesField(help_text="集群分配规则列表", default=list)


class ClusterElasticSearchConfig(UuidAuditedModel):
    """集群 ES 配置"""

    cluster = models.OneToOneField(Cluster, related_name="elastic_search_config", on_delete=models.CASCADE)
    scheme = models.CharField(help_text="ES 集群协议", max_length=12)
    host = models.CharField(help_text="ES 集群地址", max_length=128)
    port = models.IntegerField(help_text="ES 集群端口")
    username = models.CharField(help_text="ES 集群用户名", max_length=64)
    password = EncryptField(help_text="ES 集群密码")

    def as_dict(self, include_password=False) -> Dict[str, Any]:
        data = {
            "scheme": self.scheme,
            "host": self.host,
            "port": self.port,
            "username": self.username,
        }
        if include_password:
            data["password"] = self.password

        return data
