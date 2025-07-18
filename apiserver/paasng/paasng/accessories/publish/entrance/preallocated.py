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

import json
import logging
from typing import Dict, List, NamedTuple, Optional

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _

from paas_wl.infras.cluster.entities import AllocationContext
from paas_wl.infras.cluster.shim import Cluster, ClusterAllocator
from paas_wl.workloads.networking.entrance.addrs import EnvExposedURL
from paasng.accessories.publish.entrance.domains import get_preallocated_domain, get_preallocated_domains_by_env
from paasng.accessories.publish.entrance.subpaths import get_preallocated_path, get_preallocated_paths_by_env
from paasng.platform.applications.models import Application, ModuleEnvironment
from paasng.platform.engine.configurations.env_var.entities import EnvVariableList, EnvVariableObj
from paasng.platform.engine.configurations.provider import env_vars_providers
from paasng.platform.engine.constants import AppEnvName
from paasng.platform.modules.constants import ExposedURLType
from paasng.platform.modules.helpers import get_module_clusters

logger = logging.getLogger(__name__)


def get_exposed_url_type(bk_app_code: str, module_name: Optional[str] = None) -> Optional[ExposedURLType]:
    """Try to get the exposed_url_type by the given code/module, this function is useful
    when we don't know that the application has been deployed or not.

    :return: None if the application & module can not be found.
    """
    try:
        app = Application.objects.get(code=bk_app_code)
        module = app.get_module(module_name)
    except ObjectDoesNotExist:
        return None

    if type_ := module.exposed_url_type:
        return ExposedURLType(type_)
    return None


def get_preallocated_url(module_env: ModuleEnvironment) -> Optional[EnvExposedURL]:
    """获取某环境的默认访问入口地址（不含独立域名)。

    - 地址为预计算生成，无需真实部署，不保证能访问
    """
    if items := get_preallocated_urls(module_env):
        return items[0]
    return None


def get_preallocated_urls(module_env: ModuleEnvironment) -> List[EnvExposedURL]:
    """获取某环境的所有可选访问入口地址（不含独立域名)。

    - 当集群配置了多个根域时，返回多个结果
    - 地址为预计算生成，无需真实部署，不保证能访问
    """
    module = module_env.module
    if module.exposed_url_type == ExposedURLType.SUBPATH:
        subpaths = get_preallocated_paths_by_env(module_env)
        return [EnvExposedURL(url=p.as_url(), provider_type="subpath") for p in subpaths]
    elif module.exposed_url_type == ExposedURLType.SUBDOMAIN:
        domains = get_preallocated_domains_by_env(module_env)
        return [EnvExposedURL(url=d.as_url(), provider_type="subdomain") for d in domains]
    else:
        # The "exposed_url_type" is None. This should not happen in normal cases.
        logger.warning("The exposed_url_type is None when getting preallocated urls, module: %s", module)
    return []


@env_vars_providers.register_env
def _default_preallocated_urls(env: ModuleEnvironment) -> EnvVariableList:
    """Append the default preallocated URLs, the value include both "stag" and "prod" environments
    for given module.
    """
    application = env.module.application
    clusters = get_module_clusters(env.module)
    addrs_value = ""
    # Try to retrieve the exposed URL type in order to get a more accurate result.
    preferred_url_type = get_exposed_url_type(application.code, env.module.name)
    try:
        addrs = get_preallocated_address(
            application.code,
            clusters=clusters,
            module_name=env.module.name,
            preferred_url_type=preferred_url_type,
        )
        addrs_value = json.dumps(addrs._asdict())
    except ValueError:
        logger.warning("Fail to get preallocated address for application: %s, module: %s", application, env.module)
    return EnvVariableList(
        [
            EnvVariableObj.with_sys_prefix(
                key="DEFAULT_PREALLOCATED_URLS",
                value=addrs_value,
                description=_('应用模块各环境的访问地址，如 {"stag": "http://stag.com", "prod": "http://prod.com"}'),
            )
        ]
    )


class PreAddresses(NamedTuple):
    """Preallocated addresses, include both environments"""

    stag: str
    prod: str


def get_preallocated_address(
    app_code: str,
    clusters: Optional[Dict[AppEnvName, Cluster]] = None,
    module_name: Optional[str] = None,
    preferred_url_type: Optional[ExposedURLType] = None,
) -> PreAddresses:
    """Get the preallocated address for a application which was not released yet

    :param region: The region name on which the application will be deployed, if not given, use default region
    :param clusters: The env-cluster map, if not given, all use default cluster
    :param module_name: The module name, if not given, use default module
    :param preferred_url_type: The preferred type of exposed URL, default to subpath, only
        take effect when both address types are available.
    :raises: ValueError no preallocated address can be found
    """
    preferred_url_type = preferred_url_type or ExposedURLType.SUBPATH
    clusters = clusters or {}

    def _get_cluster_addr(cluster, addr_key: str) -> str:
        """A small helper function for getting address."""
        pre_subpaths = get_preallocated_path(app_code, cluster.ingress_config, module_name=module_name)
        pre_subdomains = get_preallocated_domain(app_code, cluster.ingress_config, module_name=module_name)

        if preferred_url_type == ExposedURLType.SUBDOMAIN:
            addrs = [pre_subdomains, pre_subpaths]
        else:
            addrs = [pre_subpaths, pre_subdomains]

        # Return the first non-empty address
        for addr in addrs:
            if addr:
                return getattr(addr, addr_key).as_url().as_address()
        return ""

    def _get_default_cluster(app_code: str, environment: AppEnvName) -> Cluster:
        """Get the cluster for the given application and environment"""
        try:
            app = Application.objects.get(code=app_code)
        except Application.DoesNotExist:
            # The application has not been deployed yet, but we still need to return an address
            # because other apps might depend on this non-existent application. Therefore, we will
            # attempt to get a cluster anyway, even if the result might be incorrect.
            return ClusterAllocator(AllocationContext.create_for_future_system_apps()).get_default()

        ctx = AllocationContext(tenant_id=app.tenant_id, region=app.region, environment=environment)
        return ClusterAllocator(ctx).get_default()

    # 生产环境
    prod_cluster = clusters.get(AppEnvName.PROD) or _get_default_cluster(app_code, AppEnvName.PROD)
    prod_address = _get_cluster_addr(prod_cluster, "prod")
    # 预发布环境
    stag_cluster = clusters.get(AppEnvName.STAG) or _get_default_cluster(app_code, AppEnvName.STAG)
    stag_address = _get_cluster_addr(stag_cluster, "stag")

    if not (stag_address and prod_address):
        raise ValueError(
            "failed to get sub-path or sub-domain entrance config, "
            f"stag cluster: {stag_cluster.name}, prod cluster: {prod_cluster.name}"
        )

    return PreAddresses(stag=stag_address, prod=prod_address)


def get_bk_doc_url_prefix() -> str:
    """Obtain the address prefix of the BK Document Center,
    which is used for the product document address obtained by the app
    """
    if settings.BK_DOCS_URL_PREFIX:
        return settings.BK_DOCS_URL_PREFIX

    # Address for bk_docs_center saas
    # Remove the "/" at the end to ensure that the subdomain and subpath mode are handled in the same way
    return get_preallocated_address(settings.BK_DOC_APP_ID).prod.rstrip("/")
