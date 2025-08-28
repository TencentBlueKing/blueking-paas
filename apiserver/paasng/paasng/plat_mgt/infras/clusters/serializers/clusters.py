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

from typing import Any, Dict, List, Set

from django.db.models.query import QuerySet
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from paas_wl.infras.cluster.constants import BK_LOG_DEFAULT_ENABLED, ClusterAnnotationKey, ClusterFeatureFlag
from paas_wl.infras.cluster.entities import Domain, IngressConfig
from paas_wl.infras.cluster.models import APIServer, Cluster, ClusterAppImageRegistry, ClusterElasticSearchConfig
from paas_wl.workloads.networking.egress.models import RCStateAppBinding, RegionClusterState
from paas_wl.workloads.networking.entrance.constants import AddressType
from paasng.core.tenant.user import DEFAULT_TENANT_ID, OP_TYPE_TENANT_ID
from paasng.plat_mgt.infras.clusters.constants import (
    ClusterAPIAddressType,
    ClusterAuthType,
    ClusterSource,
    TolerationEffect,
    TolerationOperator,
)
from paasng.plat_mgt.infras.clusters.state import ClusterAllocationGetter
from paasng.platform.modules.constants import ExposedURLType
from paasng.utils.validators import Base64Validator


class ElasticSearchConfigSLZ(serializers.Serializer):
    """ES 集群配置"""

    scheme = serializers.ChoiceField(choices=["http", "https"], help_text="ES 集群协议")
    host = serializers.CharField(help_text="ES 集群地址")
    port = serializers.IntegerField(help_text="ES 集群端口")
    username = serializers.CharField(help_text="ES 集群用户名")
    password = serializers.CharField(help_text="ES 集群密码")

    # TLS 配置信息
    verify_certs = serializers.BooleanField(help_text="是否验证证书", required=False)
    ca_certs = serializers.CharField(help_text="ES 集群 CA 证书", required=False)
    client_cert = serializers.CharField(help_text="ES 集群客户端证书", required=False)
    client_key = serializers.CharField(help_text="ES 集群客户端密钥", required=False)


class ImageRegistrySLZ(serializers.Serializer):
    """镜像仓库信息"""

    host = serializers.CharField(help_text="镜像仓库地址")
    skip_tls_verify = serializers.BooleanField(help_text="是否跳过 TLS 校验")
    namespace = serializers.CharField(help_text="镜像仓库命名空间")
    username = serializers.CharField(help_text="镜像仓库用户名")
    password = serializers.CharField(help_text="镜像仓库密码")


class ClusterListOutputSLZ(serializers.Serializer):
    """集群列表"""

    name = serializers.CharField(help_text="集群名称")
    bcs_cluster_id = serializers.CharField(help_text="BCS 集群 ID")
    description = serializers.CharField(help_text="集群描述")
    tenant = serializers.SerializerMethodField(help_text="所属租户名称")
    available_tenants = serializers.SerializerMethodField(help_text="可用租户列表")
    feature_flags = serializers.SerializerMethodField(help_text="已启用的特性标志名称列表")
    nodes = serializers.SerializerMethodField(help_text="集群节点列表")

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_tenant(self, obj: Cluster) -> str:
        return self.context["tenant_name_map"].get(obj.tenant_id, obj.tenant_id)

    @swagger_serializer_method(serializer_or_field=serializers.ListField(child=serializers.CharField()))
    def get_available_tenants(self, obj: Cluster) -> List[str]:
        tenant_name_map = self.context["tenant_name_map"]
        return [tenant_name_map.get(t_id, t_id) for t_id in obj.available_tenant_ids]

    @swagger_serializer_method(serializer_or_field=serializers.ListField(child=serializers.CharField()))
    def get_feature_flags(self, obj: Cluster) -> List[str]:
        return [
            ClusterFeatureFlag.get_feature_label(ff)
            for ff, enabled in obj.feature_flags.items()
            if enabled and ff in ClusterFeatureFlag
        ]

    @swagger_serializer_method(serializer_or_field=serializers.ListField(child=serializers.CharField()))
    def get_nodes(self, obj: Cluster) -> List[str]:
        # 注：虽然有 N+1 问题，但是集群数量不会很多，总体还好
        state = RegionClusterState.objects.filter(cluster_name=obj.name).first()
        if not state:
            return []

        return state.nodes_name


class ClusterAppDomainSLZ(serializers.Serializer):
    name = serializers.CharField(help_text="域名")
    https_enabled = serializers.BooleanField(help_text="是否启用 HTTPS")
    reserved = serializers.BooleanField(help_text="是否保留")


class ClusterRetrieveOutputSLZ(serializers.Serializer):
    name = serializers.CharField(help_text="集群名称")
    description = serializers.CharField(help_text="集群描述")

    cluster_source = serializers.SerializerMethodField(help_text="集群来源")
    bcs_project_id = serializers.CharField(help_text="BCS 项目 ID")
    bcs_cluster_id = serializers.CharField(help_text="BCS 集群 ID")
    bk_biz_id = serializers.CharField(help_text="蓝鲸业务 ID")
    bcs_project_name = serializers.SerializerMethodField(help_text="BCS 项目名称")
    bcs_cluster_name = serializers.SerializerMethodField(help_text="BCS 集群名称")
    bk_biz_name = serializers.SerializerMethodField(help_text="蓝鲸业务名称")

    api_address_type = serializers.SerializerMethodField(help_text="API Server 地址类型")
    api_servers = serializers.SerializerMethodField(help_text="API Server 列表")

    auth_type = serializers.SerializerMethodField(help_text="认证类型")
    ca = serializers.CharField(help_text="CA 证书", source="ca_data")
    cert = serializers.CharField(help_text="证书", source="cert_data")
    key = serializers.CharField(help_text="私钥", source="key_data")
    token = serializers.CharField(help_text="Token", source="token_value")

    container_log_dir = serializers.CharField(help_text="容器日志目录")
    access_entry_ip = serializers.SerializerMethodField(help_text="集群访问入口（一般为 clb）IP")

    elastic_search_config = serializers.SerializerMethodField(help_text="ES 集群配置")
    app_image_registry = serializers.SerializerMethodField(help_text="应用镜像仓库信息")
    available_tenant_ids = serializers.ListField(help_text="可用租户 ID 列表", child=serializers.CharField())

    component_preferred_namespace = serializers.CharField(help_text="集群组件优先部署的命名空间")
    component_image_registry = serializers.CharField(help_text="集群组件镜像仓库地址")
    app_address_type = serializers.SerializerMethodField(help_text="应用访问类型（子路径 / 子域名）")
    app_domains = serializers.SerializerMethodField(help_text="应用域名列表")

    node_selector = serializers.JSONField(help_text="节点选择器", source="default_node_selector")
    tolerations = serializers.JSONField(help_text="污点容忍度", source="default_tolerations")
    feature_flags = serializers.JSONField(help_text="特性标志")

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_cluster_source(self, obj: Cluster) -> str:
        """集群来源：如果已配置 BCS 集群信息，则认为来源是 BCS"""
        if obj.bcs_project_id and obj.bcs_cluster_id and obj.bk_biz_id:
            return ClusterSource.BCS

        return ClusterSource.NATIVE_K8S

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_bcs_project_name(self, _: Cluster) -> str:
        return self.context.get("bcs_project_name", "")

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_bcs_cluster_name(self, _: Cluster) -> str:
        return self.context.get("bcs_cluster_name", "")

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_bk_biz_name(self, _: Cluster) -> str:
        return self.context.get("bk_biz_name", "")

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_api_address_type(self, obj: Cluster) -> ClusterAPIAddressType:
        bcs_cluster_id = obj.bcs_cluster_id
        # 不是 BCS 集群，自然只能是使用自定义地址
        if not bcs_cluster_id:
            return ClusterAPIAddressType.CUSTOM

        api_servers = APIServer.objects.filter(cluster=obj)

        # BCS 网关只会有一个地址，并且访问地址中应该包含 BCS 集群 ID
        if api_servers.count() == 1 and bcs_cluster_id in api_servers[0].host:
            return ClusterAPIAddressType.BCS_GATEWAY

        return ClusterAPIAddressType.CUSTOM

    @swagger_serializer_method(serializer_or_field=serializers.ListField(child=serializers.CharField()))
    def get_api_servers(self, obj: Cluster) -> List[str]:
        return list(APIServer.objects.filter(cluster=obj).values_list("host", flat=True))

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_auth_type(self, obj: Cluster) -> ClusterAuthType:
        if obj.ca_data and obj.cert_data and obj.key_data:
            return ClusterAuthType.CERT

        return ClusterAuthType.TOKEN

    def get_access_entry_ip(self, obj: Cluster) -> str | None:
        return obj.ingress_config.frontend_ingress_ip

    @swagger_serializer_method(serializer_or_field=ElasticSearchConfigSLZ(allow_null=True))
    def get_elastic_search_config(self, obj: Cluster) -> Dict[str, Any] | None:
        if cfg := ClusterElasticSearchConfig.objects.filter(cluster=obj).first():
            return ElasticSearchConfigSLZ(cfg).data

        return None

    @swagger_serializer_method(serializer_or_field=ImageRegistrySLZ(allow_null=True))
    def get_app_image_registry(self, obj: Cluster) -> Dict[str, Any] | None:
        if registry := ClusterAppImageRegistry.objects.filter(cluster=obj).first():
            return ImageRegistrySLZ(registry).data

        return None

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_app_address_type(self, obj: Cluster) -> str:
        return ExposedURLType(obj.exposed_url_type).to_string()

    @swagger_serializer_method(serializer_or_field=ClusterAppDomainSLZ(many=True))
    def get_app_domains(self, obj: Cluster) -> List[str]:
        app_domains = (
            obj.ingress_config.sub_path_domains
            if obj.exposed_url_type == ExposedURLType.SUBPATH
            else obj.ingress_config.app_root_domains
        )

        return ClusterAppDomainSLZ(app_domains, many=True).data


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
    bcs_project_id = serializers.CharField(
        help_text="BCS 项目 ID",
        default=None,
        allow_null=True,
        allow_blank=True,
    )
    bcs_cluster_id = serializers.CharField(
        help_text="BCS 集群 ID",
        default=None,
        allow_null=True,
        allow_blank=True,
    )
    bk_biz_id = serializers.CharField(
        help_text="蓝鲸业务 ID",
        default=None,
        allow_null=True,
        allow_blank=True,
    )
    api_address_type = serializers.ChoiceField(
        help_text="k8s api 地址类型",
        choices=ClusterAPIAddressType.get_choices(),
    )
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
        validators=[Base64Validator],
        default=None,
        allow_null=True,
        allow_blank=True,
    )
    cert = serializers.CharField(
        help_text="证书",
        validators=[Base64Validator],
        default=None,
        allow_null=True,
        allow_blank=True,
    )
    key = serializers.CharField(
        help_text="私钥",
        validators=[Base64Validator],
        default=None,
        allow_null=True,
        allow_blank=True,
    )
    token = serializers.CharField(
        help_text="Token",
        default=None,
        allow_null=True,
        allow_blank=True,
    )

    # 周边组件相关配置
    container_log_dir = serializers.CharField(help_text="容器日志目录")
    access_entry_ip = serializers.IPAddressField(
        help_text="集群访问入口（一般为 clb）IP", required=False, allow_blank=True
    )

    elastic_search_config = ElasticSearchConfigSLZ(help_text="ES 集群配置", required=False, allow_null=True)
    app_image_registry = ImageRegistrySLZ(
        help_text="应用镜像仓库，若未指定则使用默认", required=False, allow_null=True
    )
    available_tenant_ids = serializers.ListField(
        help_text="可用租户 ID 列表", child=serializers.CharField(), min_length=1
    )

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        # 集群配置校验
        self._validate_cluster_configs(attrs)
        # 认证配置校验
        self._validate_auth_configs(attrs)
        # ES 配置校验
        self._validate_elastic_search_config(attrs)
        # 集群应用镜像仓库校验
        self._validate_app_image_registry(attrs)
        # 可用租户 ID 列表校验
        self._validate_available_tenant_ids(attrs)

        # 清理无效的认证数据，避免混淆
        if attrs["auth_type"] == ClusterAuthType.CERT:
            attrs["token"] = None
        else:
            attrs["ca"] = attrs["cert"] = attrs["key"] = None

        return attrs

    @staticmethod
    def _validate_cluster_configs(attrs: Dict[str, Any]):
        cluster_source = attrs["cluster_source"]
        api_address_type = attrs["api_address_type"]

        bcs_project_id = attrs.get("bcs_project_id")
        bcs_cluster_id = attrs.get("bcs_cluster_id")
        bk_biz_id = attrs.get("bk_biz_id")
        api_servers = attrs.get("api_servers", [])

        if cluster_source == ClusterSource.BCS:
            if not (bcs_project_id and bcs_cluster_id and bk_biz_id):
                raise ValidationError(_("BCS 集群必须提供项目，集群，业务信息"))

            if api_address_type == ClusterAPIAddressType.BCS_GATEWAY:
                if len(api_servers) != 1:
                    raise ValidationError(_("BCS 集群必须提供且仅提供一个 API Server"))

                if bcs_cluster_id not in api_servers[0]:
                    raise ValidationError(_("API 地址类型为 BCS 网关时，API Server 中必须包含 BCS 集群 ID"))

        elif api_address_type == ClusterAPIAddressType.BCS_GATEWAY:
            raise ValidationError(_("原生 K8S 集群不支持使用 BCS 网关作为 API 地址类型"))

        # 检查 API Server 地址是否合法
        for srv in api_servers:
            if not srv.startswith("http"):
                raise ValidationError(_("API Server 地址必须以 http 或 https 开头"))

    @staticmethod
    def _validate_auth_configs(attrs: Dict[str, Any]):
        auth_type = attrs["auth_type"]
        if auth_type == ClusterAuthType.CERT and not (attrs.get("ca") and attrs.get("cert") and attrs.get("key")):
            raise ValidationError(_("集群认证方式为证书时，CA 证书 + 证书 + 私钥 必须同时提供"))

        if auth_type == ClusterAuthType.TOKEN and not attrs.get("token"):
            raise ValidationError(_("集群认证方式为 Token 时，Token 必须提供"))

    @staticmethod
    def _validate_elastic_search_config(attrs: Dict[str, Any]):
        # 若启用蓝鲸日志平台方案，则 ES 配置是可选的
        if BK_LOG_DEFAULT_ENABLED:
            return

        if not attrs.get("elastic_search_config"):
            raise ValidationError(_("ES 集群配置是必填项"))

    def _validate_app_image_registry(self, attrs: Dict[str, Any]):
        # 创建时提供的 cur_tenant_id，更新时提供的是 cur_cluster
        cur_tenant_id = self.context.get("cur_tenant_id") or self.context["cur_cluster"].tenant_id

        # 默认 / 运营租户可以不配置应用集群镜像仓库（使用 settings 中的默认配置）
        # 如果是接入默认 / 运营租户的第三方集群，理论上是不该使用默认的全局配置的，
        # 但是这由接入的管理员决定，平台不做限制（这两租户的管理员都是平台管理员）
        if cur_tenant_id in [DEFAULT_TENANT_ID, OP_TYPE_TENANT_ID]:
            return

        # 其他普通租户都需要配置集群应用镜像凭证，不能使用全局配置以免泄露到第三方集群
        if not attrs.get("app_image_registry"):
            raise ValidationError(_("当前租户必须提供应用镜像仓库"))

    def _validate_available_tenant_ids(self, attrs: Dict[str, Any]):
        if self.context["cur_tenant_id"] not in attrs["available_tenant_ids"]:
            raise ValidationError(_("集群所属租户 ID {} 不在可用租户 ID 列表中").format(self.context["cur_tenant_id"]))

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
    value = serializers.CharField(help_text="值", default=None, allow_blank=True, allow_null=True, required=False)
    effect = serializers.ChoiceField(help_text="效果", choices=TolerationEffect.get_choices())
    tolerationSeconds = serializers.IntegerField(help_text="容忍秒数", min_value=0, default=0, required=False)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        op = attrs["operator"]

        if op == TolerationOperator.EQUAL:
            if not attrs.get("value"):
                raise ValidationError(_("运算符为 Equal 时，值（value）必须提供"))
        elif op == TolerationOperator.EXISTS:
            # 如果运算符为 Exists，则不能提供 value
            attrs.pop("value", None)

        # 但效果不是 NO_EXECUTE 时，不可以提供容忍秒数
        if attrs["effect"] != TolerationEffect.NO_EXECUTE:
            attrs.pop("tolerationSeconds", None)

        return attrs


class ClusterUpdateInputSLZ(ClusterCreateInputSLZ):
    """集群更新"""

    app_address_type = serializers.ChoiceField(
        help_text="应用访问地址类型",
        choices=(AddressType.SUBPATH, AddressType.SUBDOMAIN),
        default=AddressType.SUBPATH,
    )
    app_domains = serializers.ListField(help_text="应用域名配置", child=AppDomainConfigSLZ(), default=list)

    component_preferred_namespace = serializers.CharField(help_text="组件部署首选命名空间")
    component_image_registry = serializers.CharField(help_text="组件镜像仓库")

    feature_flags = serializers.JSONField(help_text="特性标志", default=dict)
    node_selector = serializers.JSONField(help_text="节点选择器", default=dict)
    tolerations = serializers.ListField(help_text="污点容忍度", child=TolerationSLZ(), default=list)

    def validate_name(self, name: str) -> str:
        cur_cluster = self.context["cur_cluster"]
        if name != cur_cluster.name:
            raise ValidationError(_("集群名称不可修改"))

        return name

    def validate_available_tenant_ids(self, available_tenant_ids: List[str]) -> List[str]:
        # 判断租户 ID 列表是否有包含所有已配置策略的租户
        allocated_tenant_ids = ClusterAllocationGetter(self.context["cur_cluster"]).get_allocated_tenant_ids()

        if used_tenant_ids := set(allocated_tenant_ids) - set(available_tenant_ids):
            raise ValidationError(_("当前集群已被租户 {} 分配，无法变更可用租户").format(used_tenant_ids))

        return available_tenant_ids

    def validate_feature_flags(self, feature_flags: Dict[str, bool]) -> Dict[str, bool]:
        if not isinstance(feature_flags, dict):
            raise ValidationError(_("特性标志必须为字典"))

        # 不合法的特性标志 / 非布尔类型的值，直接忽略（历史遗留的脏数据）
        return {k: v for k, v in feature_flags.items() if k in ClusterFeatureFlag and isinstance(v, bool)}

    def validate_node_selector(self, node_selector: Dict[str, str]) -> Dict[str, str]:
        if not isinstance(node_selector, dict):
            raise ValidationError(_("节点选择器必须为字典"))

        for k, v in node_selector.items():
            if not isinstance(k, str):
                raise ValidationError(_("节点选择器 key 必须为字符串"))
            if not isinstance(v, str):
                raise ValidationError(_("节点选择器 value 必须为字符串"))

        return node_selector

    def _validate_available_tenant_ids(self, attrs: Dict[str, Any]):
        cur_tenant_id = self.context["cur_cluster"].tenant_id

        if cur_tenant_id not in attrs["available_tenant_ids"]:
            raise ValidationError(_("集群所属租户 ID {} 不在可用租户 ID 列表中").format(cur_tenant_id))

    def to_internal_value(self, data: Dict[str, Any]) -> Dict[str, Any]:
        data = super().to_internal_value(data)

        cur_cluster = self.context["cur_cluster"]
        # 子路径 / 子域名相关转换
        domains = [
            Domain(name=d["name"], reserved=d["reserved"], https_enabled=d["https_enabled"])
            for d in data["app_domains"]
        ]
        if data["app_address_type"] == AddressType.SUBPATH:
            data["ingress_config"].sub_path_domains = domains
            # 允许保留集群已有的子域名配置
            data["ingress_config"].app_root_domains = cur_cluster.ingress_config.app_root_domains
        else:
            data["ingress_config"].app_root_domains = domains
            # 允许保留集群已有的子路径配置
            data["ingress_config"].sub_path_domains = cur_cluster.ingress_config.sub_path_domains

        return data


class ClusterStatusRetrieveOutputSLZ(serializers.Serializer):
    basic = serializers.BooleanField(help_text="基础配置")
    component = serializers.BooleanField(help_text="组件配置")
    feature = serializers.BooleanField(help_text="集群特性")


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
    bound_app_module_envs = serializers.ListField(help_text="已绑定的应用部署环境", child=AppModuleEnvSLZ())


class ClusterNodesStateSLZ(serializers.Serializer):
    nodes = serializers.ListField(child=serializers.CharField(), help_text="节点信息", source="nodes_name")
    binding_apps = serializers.SerializerMethodField(help_text="绑定应用")
    created_at = serializers.DateTimeField(help_text="同步时间", source="created")

    def get_binding_apps(self, obj: RegionClusterState) -> List[str]:
        bindings: QuerySet[RCStateAppBinding] = RCStateAppBinding.objects.filter(state_id=obj.id).select_related("app")
        app_codes: Set[str] = set()

        for binding in bindings:
            if binding.app:
                app_codes.add(binding.app.paas_app_code)

        return list(app_codes)


class ClusterNodesStateRetrieveOutputSLZ(ClusterNodesStateSLZ):
    """节点信息序列化器"""


class ClusterNodesStateSyncRecordListOutputSLZ(ClusterNodesStateSLZ):
    """节点同步记录序列化器"""

    id = serializers.IntegerField(help_text="状态记录 ID")
