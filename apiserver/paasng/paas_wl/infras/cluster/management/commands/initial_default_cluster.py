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

from typing import Dict, List

from attr import define
from blue_krill.data_types.enum import StrStructuredEnum
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from environ import Env

from paas_wl.infras.cluster.components import get_default_component_configs
from paas_wl.infras.cluster.constants import ClusterAllocationPolicyType, ClusterFeatureFlag
from paas_wl.infras.cluster.entities import AllocationPolicy
from paas_wl.infras.cluster.models import (
    APIServer,
    Cluster,
    ClusterAllocationPolicy,
    ClusterComponent,
    ClusterElasticSearchConfig,
)
from paas_wl.infras.resources.base.base import invalidate_global_configuration_pool
from paasng.core.tenant.user import get_init_tenant_id

env = Env()


class EnvVarKey(StrStructuredEnum):
    """环境变量键名"""

    APP_ROOT_DOMAIN = "PAAS_WL_CLUSTER_APP_ROOT_DOMAIN"
    SUB_PATH_DOMAIN = "PAAS_WL_CLUSTER_SUB_PATH_DOMAIN"
    HTTPS_ENABLED = "PAAS_WL_CLUSTER_ENABLED_HTTPS_BY_DEFAULT"
    FRONTEND_INGRESS_IP = "PAAS_WL_CLUSTER_FRONTEND_INGRESS_IP"
    HTTP_PORT = "PAAS_WL_CLUSTER_HTTP_PORT"
    HTTPS_PORT = "PAAS_WL_CLUSTER_HTTPS_PORT"

    BCS_CLUSTER_ID = "PAAS_WL_CLUSTER_BCS_CLUSTER_ID"
    BCS_PROJECT_ID = "PAAS_WL_CLUSTER_BCS_PROJECT_ID"
    BK_BIZ_ID = "PAAS_WL_CLUSTER_BK_BIZ_ID"

    API_SERVER_URLS = "PAAS_WL_CLUSTER_API_SERVER_URLS"
    CA = "PAAS_WL_CLUSTER_CA_DATA"
    CERT = "PAAS_WL_CLUSTER_CERT_DATA"
    KEY = "PAAS_WL_CLUSTER_KEY_DATA"
    TOKEN = "PAAS_WL_CLUSTER_TOKEN_VALUE"

    FEATURE_FLAGS = "PAAS_WL_CLUSTER_FEATURE_FLAGS"
    NODE_SELECTOR = "PAAS_WL_CLUSTER_NODE_SELECTOR"
    TOLERATIONS = "PAAS_WL_CLUSTER_TOLERATIONS"


@define
class InitialClusterData:
    # 基础配置
    uuid: str
    name: str
    tenant_id: str
    description: str
    ingress_config: Dict
    annotations: Dict
    # 访问凭证 - 证书
    ca_data: str | None
    cert_data: str | None
    key_data: str | None
    # 访问凭证 - Token
    token_value: str | None
    # 高级特性
    default_node_selector: Dict
    default_tolerations: List[Dict]
    feature_flags: Dict
    # ApiServer
    api_server_urls: List[str]


class Command(BaseCommand):
    help = "Initialize the application cluster, which can overwrite the existing data in the database"

    def add_arguments(self, parser):
        parser.add_argument("--overwrite", dest="overwrite", action="store_true")
        parser.add_argument("--dry_run", dest="dry_run", action="store_true")

    def handle(self, overwrite, dry_run, *args, **options):
        data = self._build_cluster_data()

        if dry_run:
            self.stdout.write(f"DRY-RUN: preparing to initialize the cluster, data: {data}")
            return

        if Cluster.objects.filter(pk=data.uuid).exists() and not overwrite:
            self.stderr.write(
                f"Cluster (uuid: {data.uuid}, name: {data.name}) exists and not allow to overwrite, skip"
            )
            return

        # 更新 / 创建集群及相关资源配置
        with transaction.atomic(using="workloads"):
            self._upsert_cluster_and_related_configs(data)

        # 禁用内存中的集群资源池配置，使其重新加载
        invalidate_global_configuration_pool()

        self.stdout.write(f"Successfully initialized the cluster {data.name} in tenant {data.tenant_id}")

    def _build_cluster_data(self) -> InitialClusterData:
        """根据环境变量 / 项目配置构建集群数据"""
        # 网络相关配置
        app_root_domain = env.str(EnvVarKey.APP_ROOT_DOMAIN, "")
        sub_path_domain = env.str(EnvVarKey.SUB_PATH_DOMAIN, "")
        # 至少需要配置 子域名 / 子路径 的域名
        if not (app_root_domain or sub_path_domain):
            raise ValueError(f"{EnvVarKey.APP_ROOT_DOMAIN} or {EnvVarKey.SUB_PATH_DOMAIN} must be set")

        https_enabled = env.bool(EnvVarKey.HTTPS_ENABLED, False)
        ingress_config = {
            "default_ingress_domain_tmpl": "%s." + sub_path_domain,
            "frontend_ingress_ip": env.str(EnvVarKey.FRONTEND_INGRESS_IP, ""),
            "app_root_domains": (
                [{"name": app_root_domain, "https_enabled": https_enabled}] if app_root_domain else []
            ),
            "sub_path_domains": (
                [{"name": sub_path_domain, "https_enabled": https_enabled}] if sub_path_domain else []
            ),
            "port_map": {
                "http": env.int(EnvVarKey.HTTP_PORT, 80),
                "https": env.int(EnvVarKey.HTTPS_PORT, 443),
            },
        }

        # Api 访问地址
        api_server_urls = env.json(EnvVarKey.API_SERVER_URLS, [])
        if not api_server_urls:
            raise ValueError(f"{EnvVarKey.API_SERVER_URLS} (json list format) must be set")

        # BCS 集群相关配置
        bcs_cluster_id = env.str(EnvVarKey.BCS_CLUSTER_ID, "")
        bcs_project_id = env.str(EnvVarKey.BCS_PROJECT_ID, "")
        bk_biz_id = env.str(EnvVarKey.BK_BIZ_ID, "")

        # 集群，项目，业务 ID 必须全都有值，或者全都无值
        if bcs_cluster_id and bcs_project_id and bk_biz_id:
            annotations = {
                "bcs_cluster_id": bcs_cluster_id,
                "bcs_project_id": bcs_project_id,
                "bk_biz_id": bk_biz_id,
            }
        elif not bcs_cluster_id and not bcs_project_id and not bk_biz_id:
            self.stderr.write("No BCS cluster info found, set annotations as empty dict")
            annotations = {}
        else:
            raise ValueError(
                f"{EnvVarKey.BCS_CLUSTER_ID}, {EnvVarKey.BCS_PROJECT_ID}, "
                + f"{EnvVarKey.BK_BIZ_ID} must be all set or all unset"
            )

        # 证书 / Token 相关配置
        ca_data = env.str(EnvVarKey.CA, "")
        cert_data = env.str(EnvVarKey.CERT, "")
        key_data = env.str(EnvVarKey.KEY, "")
        token_value = env.str(EnvVarKey.TOKEN, "")

        if not ((ca_data and cert_data and key_data) or token_value):
            raise ValueError(f"{EnvVarKey.CA}, {EnvVarKey.CERT}, {EnvVarKey.KEY} or {EnvVarKey.TOKEN} must be set")

        # 集群功能特性
        feature_flags = env.json(EnvVarKey.FEATURE_FLAGS, {})
        if feature_flags:
            # 过滤掉不合法的值（非法 key / value）
            feature_flags = {k: v for k, v in feature_flags.items() if k in ClusterFeatureFlag and v is not None}
        else:
            self.stdout.write("No feature flags found, using default feature flags")
            feature_flags = ClusterFeatureFlag.get_default_flags()

        # 节点选择器 & 污点容忍度
        node_selector = env.json(EnvVarKey.NODE_SELECTOR, {})
        tolerations = env.json(EnvVarKey.TOLERATIONS, [])

        return InitialClusterData(
            # 固定 uuid & 集群名称
            uuid="332d740b-03ed-40f2-aa6b-c90cc5f1e89c",
            name="default-main",
            tenant_id=get_init_tenant_id(),
            description="default blueking application cluster",
            ingress_config=ingress_config,
            annotations=annotations,
            ca_data=ca_data,
            cert_data=cert_data,
            key_data=key_data,
            token_value=token_value,
            default_node_selector=node_selector,
            default_tolerations=tolerations,
            feature_flags=feature_flags,
            api_server_urls=api_server_urls,
        )

    def _upsert_cluster_and_related_configs(self, data: InitialClusterData):
        # 1. 创建 / 更新集群
        cluster, _ = Cluster.objects.update_or_create(
            uuid=data.uuid,
            name=data.name,
            defaults={
                "tenant_id": data.tenant_id,
                "description": data.description,
                "ingress_config": data.ingress_config,
                "annotations": data.annotations,
                "ca_data": data.ca_data,
                "cert_data": data.cert_data,
                "key_data": data.key_data,
                "token_value": data.token_value,
                "default_node_selector": data.default_node_selector,
                "default_tolerations": data.default_tolerations,
                "feature_flags": data.feature_flags,
                "available_tenant_ids": [data.tenant_id],
            },
        )

        # 2. 创建集群的 API Server，采用先删除后添加的方式
        APIServer.objects.filter(cluster=cluster).delete()
        APIServer.objects.bulk_create(
            [APIServer(cluster=cluster, host=url, tenant_id=cluster.tenant_id) for url in data.api_server_urls]
        )

        # 3. 创建集群组件配置，采用先删除后添加的方式
        ClusterComponent.objects.filter(cluster=cluster).delete()
        ClusterComponent.objects.bulk_create(
            [
                ClusterComponent(cluster=cluster, name=cfg["name"], required=cfg["required"])
                for cfg in get_default_component_configs()
            ]
        )

        # 4. 创建集群关联的日志配置
        if not settings.ELASTICSEARCH_HOSTS:
            raise ValueError("ELASTICSEARCH_HOSTS is not configured!")

        conf = settings.ELASTICSEARCH_HOSTS[0]
        host, port = conf["host"], conf["port"]
        username, _, password = conf["http_auth"].partition(":")
        scheme = "https" if conf.get("use_ssl") else "http"

        # ES 集群 TLS 配置
        verify_certs = conf.get("verify_certs", False)
        ca_certs = conf.get("ca_certs")
        client_cert = conf.get("client_cert")
        client_key = conf.get("client_key")

        ClusterElasticSearchConfig.objects.update_or_create(
            cluster=cluster,
            defaults={
                "scheme": scheme,
                "host": host,
                "port": port,
                "username": username,
                "password": password,
                "verify_certs": verify_certs,
                "ca_certs": ca_certs,
                "client_cert": client_cert,
                "client_key": client_key,
                "tenant_id": cluster.tenant_id,
            },
        )

        # 5. 检查集群分配策略，若不存在，则创建默认的分配策略
        if not ClusterAllocationPolicy.objects.filter(tenant_id=cluster.tenant_id).exists():
            ClusterAllocationPolicy.objects.create(
                tenant_id=cluster.tenant_id,
                type=ClusterAllocationPolicyType.UNIFORM,
                allocation_policy=AllocationPolicy(env_specific=False, clusters=[cluster.name]),
            )
