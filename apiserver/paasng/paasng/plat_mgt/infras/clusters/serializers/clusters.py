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

import base64
from typing import Any, Dict, List

from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paas_wl.infras.cluster.constants import ClusterAnnotationKey, ClusterFeatureFlag
from paas_wl.infras.cluster.entities import Domain, IngressConfig
from paas_wl.infras.cluster.models import APIServer, Cluster, ClusterElasticSearchConfig
from paas_wl.workloads.networking.egress.models import RegionClusterState
from paas_wl.workloads.networking.entrance.constants import AddressType
from paasng.plat_mgt.constants import SENSITIVE_MASK
from paasng.plat_mgt.infras.clusters.constants import (
    ClusterAuthType,
    ClusterSource,
    TolerationEffect,
    TolerationOperator,
)


def ensure_base64_encoded(content: str) -> None:
    """确保内容是 base64 编码的"""
    try:
        base64.b64decode(content)
    except Exception:
        raise ValidationError("content isn't base64 encoded.")


class ElasticSearchConfigSLZ(serializers.Serializer):
    """ES 集群配置"""

    scheme = serializers.ChoiceField(choices=["http", "https"], help_text="ES 集群协议")
    host = serializers.CharField(help_text="ES 集群地址")
    port = serializers.IntegerField(help_text="ES 集群端口")
    username = serializers.CharField(help_text="ES 集群用户名")
    password = serializers.CharField(help_text="ES 集群密码")


class ClusterListOutputSLZ(serializers.Serializer):
    """集群列表"""

    name = serializers.CharField(help_text="集群名称")
    bcs_cluster_id = serializers.CharField(help_text="BCS 集群 ID")
    description = serializers.CharField(help_text="集群描述")
    tenant = serializers.SerializerMethodField(help_text="所属租户名称")
    available_tenants = serializers.SerializerMethodField(help_text="可用租户列表")
    feature_flags = serializers.ListField(help_text="特性标志名称列表", child=serializers.CharField())
    nodes = serializers.SerializerMethodField(help_text="集群节点列表")

    def get_tenant(self, obj: Cluster) -> str:
        # FIXME（多租户）这里应该把 ID 转换成名称
        return obj.tenant_id

    def get_available_tenants(self, obj: Cluster) -> str:
        # FIXME（多租户）这里应该把 ID 转换成名称
        return obj.available_tenant_ids

    def get_nodes(self, obj: Cluster) -> List[str]:
        # 注：虽然有 N+1 问题，但是集群数量不会很多，总体还好
        state = RegionClusterState.objects.filter(cluster_name=obj.name).first()
        if not state:
            return []

        return state.nodes_name


class ClusterRetrieveOutputSLZ(serializers.Serializer):
    name = serializers.CharField(help_text="集群名称")
    description = serializers.CharField(help_text="集群描述")

    cluster_source = serializers.SerializerMethodField(help_text="集群来源")
    bcs_project_id = serializers.CharField(help_text="BCS 项目 ID")
    bcs_cluster_id = serializers.CharField(help_text="BCS 集群 ID")
    bk_biz_id = serializers.CharField(help_text="蓝鲸业务 ID")
    api_servers = serializers.SerializerMethodField(help_text="API Server 列表")

    auth_type = serializers.SerializerMethodField(help_text="认证类型")
    # 注：敏感配置不会再次暴露给前端，使用 MASK 替换（这里使用 default 是可以的，原始 key 与这里的不同）
    ca = serializers.CharField(help_text="CA 证书", default=SENSITIVE_MASK)
    cert = serializers.CharField(help_text="证书", default=SENSITIVE_MASK)
    key = serializers.CharField(help_text="私钥", default=SENSITIVE_MASK)
    token = serializers.CharField(help_text="Token", default=SENSITIVE_MASK)

    container_log_dir = serializers.CharField(help_text="容器日志目录")
    access_entry_ip = serializers.SerializerMethodField(help_text="集群访问入口（一般为 clb）IP")

    elastic_search_config = serializers.SerializerMethodField(help_text="ES 集群配置")
    available_tenant_ids = serializers.ListField(help_text="可用租户 ID 列表", child=serializers.CharField())

    node_selector = serializers.JSONField(help_text="节点选择器", source="default_node_selector")
    tolerations = serializers.JSONField(help_text="污点容忍度", source="default_tolerations")
    feature_flags = serializers.JSONField(help_text="特性标志")

    def get_cluster_source(self, obj: Cluster) -> str:
        """集群来源：如果已配置 BCS 集群信息，则认为来源是 BCS"""
        if obj.bcs_project_id and obj.bcs_cluster_id and obj.bk_biz_id:
            return ClusterSource.BCS

        return ClusterSource.NATIVE_K8S

    def get_api_servers(self, obj: Cluster) -> List[str]:
        return list(APIServer.objects.filter(cluster=obj).values_list("host", flat=True))

    def get_auth_type(self, obj: Cluster) -> ClusterAuthType:
        if obj.ca_data and obj.cert_data and obj.key_data:
            return ClusterAuthType.CERT

        return ClusterAuthType.TOKEN

    def get_access_entry_ip(self, obj: Cluster) -> str | None:
        return obj.ingress_config.frontend_ingress_ip

    @swagger_serializer_method(serializer_or_field=ElasticSearchConfigSLZ())
    def get_elastic_search_config(self, obj: Cluster) -> Dict[str, Any]:
        cfg = ClusterElasticSearchConfig.objects.filter(cluster=obj).first()
        if not cfg:
            return {}

        # 同上，ES 配置中的密码信息也是敏感配置，不会再次暴露给前端
        cfg.password = SENSITIVE_MASK
        return ElasticSearchConfigSLZ(cfg).data


class ClusterCreateInputSLZ(serializers.Serializer):
    """集群创建"""

    name = serializers.RegexField(
        help_text="集群名称",
        regex=r"^[A-Za-z0-9-]+$",
        min_length=3,
        max_length=32,
    )
    description = serializers.CharField(help_text="集群描述", max_length=256)
    cluster_source = serializers.ChoiceField(
        help_text="集群来源",
        choices=ClusterSource.get_choices(),
    )
    # bcs 集群特殊配置
    bcs_project_id = serializers.CharField(help_text="BCS 项目 ID", required=False)
    bcs_cluster_id = serializers.CharField(help_text="BCS 集群 ID", required=False)
    bk_biz_id = serializers.CharField(help_text="蓝鲸业务 ID", required=False)
    # 注：虽然 bcs 集群只需要一个 server，也统一为列表结构
    api_servers = serializers.ListField(
        help_text="API Server 列表",
        child=serializers.CharField(),
        min_length=1,
    )
    auth_type = serializers.ChoiceField(
        help_text="认证类型",
        choices=ClusterAuthType.get_choices(),
    )
    # ca + cert + key / token 二选一
    ca = serializers.CharField(
        help_text="CA 证书",
        validators=[ensure_base64_encoded],
        default=None,
        allow_blank=True,
    )
    cert = serializers.CharField(
        help_text="证书",
        validators=[ensure_base64_encoded],
        default=None,
        allow_blank=True,
    )
    key = serializers.CharField(
        help_text="私钥",
        validators=[ensure_base64_encoded],
        default=None,
        allow_blank=True,
    )
    token = serializers.CharField(help_text="Token", default=None, allow_blank=True)

    # 周边组件相关配置
    container_log_dir = serializers.CharField(help_text="容器日志目录")
    access_entry_ip = serializers.IPAddressField(
        help_text="集群访问入口（一般为 clb）IP", required=False, allow_blank=True
    )

    elastic_search_config = ElasticSearchConfigSLZ(help_text="ES 集群配置")
    available_tenant_ids = serializers.ListField(
        help_text="可用租户 ID 列表", child=serializers.CharField(), min_length=1
    )

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        # BCS 集群特殊配置校验
        if attrs["cluster_source"] == ClusterSource.BCS:
            if not (attrs.get("bcs_project_id") and attrs.get("bcs_cluster_id") and attrs.get("bk_biz_id")):
                raise ValidationError(_("BCS 集群必须提供项目，集群，业务信息"))

            if len(attrs.get("api_servers", [])) != 1:
                raise ValidationError(_("BCS 集群必须提供且仅提供一个 API Server"))

        # 认证配置校验
        auth_type = attrs["auth_type"]
        if auth_type == ClusterAuthType.CERT:
            if not (attrs.get("ca") and attrs.get("cert") and attrs.get("key")):
                raise ValidationError(_("集群认证方式为证书时，CA 证书 + 证书 + 私钥 必须同时提供"))
        elif auth_type == ClusterAuthType.TOKEN:
            if not attrs.get("token"):
                raise ValidationError(_("集群认证方式为 Token 时，Token 必须提供"))
        else:
            raise ValidationError(_("集群认证方式 {} 不合法").format(auth_type))

        # 清理无效的认证数据，避免混淆
        if auth_type == ClusterAuthType.CERT:
            attrs["token"] = None
        else:
            attrs["ca"] = attrs["cert"] = attrs["key"] = None

        return attrs

    def validate_name(self, name: str) -> str:
        if Cluster.objects.filter(name=name).exists():
            raise ValidationError(_("集群名称 {} 已被使用").format(name))

        return name

    def to_internal_value(self, data: Dict[str, Any]) -> Dict[str, Any]:
        data = super().to_internal_value(data)

        # 目前只有 BCS 集群需要使用注解
        data["annotations"] = (
            {
                ClusterAnnotationKey.BCS_PROJECT_ID: data["bcs_project_id"],
                ClusterAnnotationKey.BCS_CLUSTER_ID: data["bcs_cluster_id"],
                ClusterAnnotationKey.BK_BIZ_ID: data["bk_biz_id"],
            }
            if data["cluster_source"] == ClusterSource.BCS
            else {}
        )

        data["ingress_config"] = IngressConfig(
            frontend_ingress_ip=data.get("access_entry_ip", ""),
        )

        return data


class AppDomainConfigSLZ(serializers.Serializer):
    """应用域名配置"""

    name = serializers.RegexField(help_text="域名", regex=r"^[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+$", max_length=128)
    https_enabled = serializers.BooleanField(help_text="是否启用 HTTPS", default=False)
    reserved = serializers.BooleanField(help_text="是否保留", default=False)


class TolerationSLZ(serializers.Serializer):
    """K8S 容忍度项"""

    key = serializers.CharField(help_text="键")
    operator = serializers.ChoiceField(help_text="运算符", choices=TolerationOperator.get_choices())
    value = serializers.CharField(help_text="值", default=None, required=False)
    effect = serializers.ChoiceField(help_text="效果", choices=TolerationEffect.get_choices())
    tolerationSeconds = serializers.IntegerField(help_text="容忍秒数", min_value=0, default=0, required=False)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        if attrs["operator"] == TolerationOperator.EQUAL:
            if not attrs.get("value"):
                raise ValidationError(_("运算符为 Equal 时，值（value）必须提供"))
        elif attrs.get("value"):
            raise ValidationError(_("运算符不为 Equal 时，值（value）需为空"))

        return attrs


class ClusterUpdateInputSLZ(ClusterCreateInputSLZ):
    """集群更新"""

    app_address_type = serializers.ChoiceField(
        help_text="应用访问地址类型",
        choices=(AddressType.SUBPATH, AddressType.SUBPATH),
        default=AddressType.SUBPATH,
    )
    app_domains = serializers.ListField(help_text="应用域名配置", child=AppDomainConfigSLZ(), default=list)

    component_preferred_namespace = serializers.CharField(help_text="组件部署首选命名空间")
    component_image_registry = serializers.CharField(help_text="组件镜像仓库")

    feature_flags = serializers.JSONField(help_text="特性标志", default=dict)
    node_selector = serializers.JSONField(help_text="节点选择器", default=dict)
    tolerations = serializers.ListField(help_text="污点容忍度", child=TolerationSLZ(), default=list)

    def validate_name(self, name: str) -> str:
        if name != self.context["cur_cluster_name"]:
            raise ValidationError(_("集群名称不可修改"))

        return name

    def validate_feature_flags(self, feature_flags: Dict[str, bool]) -> Dict[str, bool]:
        if not isinstance(feature_flags, dict):
            raise ValidationError(_("特性标志必须为字典"))

        for k, v in feature_flags.items():
            try:
                ClusterFeatureFlag(k)
            except ValueError:
                raise ValidationError(_("特性标志 {} 不合法").format(k))

            if not isinstance(v, bool):
                raise ValidationError(_("特性标志的值必须为布尔值"))

        return feature_flags

    def validate_node_selector(self, node_selector: Dict[str, str]) -> Dict[str, str]:
        if not isinstance(node_selector, dict):
            raise ValidationError(_("节点选择器必须为字典"))

        for k, v in node_selector.items():
            if not isinstance(k, str):
                raise ValidationError(_("节点选择器 key 必须为字符串"))
            if not isinstance(v, str):
                raise ValidationError(_("节点选择器 value 必须为字符串"))

        return node_selector

    def to_internal_value(self, data: Dict[str, Any]) -> Dict[str, Any]:
        data = super().to_internal_value(data)

        cur_cluster = self.context["cur_cluster"]
        # 对于敏感信息，需要支持如果是提交的 MASK，则使用原始数据库中的值
        data["ca"] = data["ca"] if data["ca"] != SENSITIVE_MASK else cur_cluster.ca_data
        data["cert"] = data["cert"] if data["cert"] != SENSITIVE_MASK else cur_cluster.cert_data
        data["key"] = data["key"] if data["key"] != SENSITIVE_MASK else cur_cluster.key_data
        data["token"] = data["token"] if data["token"] != SENSITIVE_MASK else cur_cluster.token_value

        # 子路径 / 子域名相关转换
        domains = [
            Domain(name=d["name"], reserved=d["reserved"], https_enabled=d["https_enabled"])
            for d in data["app_domains"]
        ]
        if data["app_address_type"] == AddressType.SUBPATH:
            data["ingress_config"].sub_path_domains = domains
        else:
            data["ingress_config"].app_root_domains = domains

        return data


class AppModuleEnvSLZ(serializers.Serializer):
    app_code = serializers.CharField(help_text="应用 Code")
    module_name = serializers.CharField(help_text="模块名称")
    environment = serializers.CharField(help_text="部署环境")


class ClusterUsageRetrieveOutputSLZ(serializers.Serializer):
    """集群被使用的情况"""

    available_tenant_ids = serializers.ListField(help_text="可用租户 ID 列表", child=serializers.CharField())
    allocated_tenant_ids = serializers.ListField(
        help_text="已有集群分配策略租户 ID 列表", child=serializers.CharField()
    )
    bind_app_module_envs = serializers.ListField(help_text="已绑定的应用部署环境", child=AppModuleEnvSLZ())
