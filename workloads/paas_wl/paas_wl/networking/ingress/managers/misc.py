# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
import logging
from typing import Iterable, List, NamedTuple

from paas_wl.cluster.utils import get_cluster_by_app
from paas_wl.networking.ingress.entities.ingress import PIngressDomain
from paas_wl.networking.ingress.exceptions import EmptyAppIngressError
from paas_wl.networking.ingress.managers.base import AppIngressMgr
from paas_wl.networking.ingress.managers.domain import CustomDomainIngressMgr, SubdomainAppIngressMgr
from paas_wl.networking.ingress.managers.subpath import SubPathAppIngressMgr
from paas_wl.networking.ingress.models import Domain
from paas_wl.platform.applications.models import App
from paas_wl.platform.applications.struct_models import get_env_by_engine_app_id
from paas_wl.resources.kube_res.exceptions import AppEntityNotFound

logger = logging.getLogger(__name__)


class UpdateTargetResult(NamedTuple):
    """Result type for `AppDefaultIngresses.safe_update_target`"""

    num_of_successful: int
    num_of_nonexistent: int


class AppDefaultIngresses:
    """helps managing app's default ingress rules."""

    def __init__(self, app: App):
        self.app = app

    def list(self) -> Iterable[AppIngressMgr]:
        """Return app's all default manger objects"""

        yield LegacyAppIngressMgr(self.app)
        yield SubdomainAppIngressMgr(self.app)
        yield SubPathAppIngressMgr(self.app)

        # Independent domain managers
        # NOTE: get_env_by_engine_app_id 会产生 1 次网络请求(依赖 apiserver 服务)
        # TODO: 添加查询缓存，或尽早合并项目减少模块之间的网络调用
        env = get_env_by_engine_app_id(self.app.pk)
        for domain in Domain.objects.filter(module_id=env.module_id, environment_id=env.id):
            yield CustomDomainIngressMgr(self.app, domain)

    def sync_ignore_empty(self, default_service_name: str = None):
        """Sync current ingress resources to apiserver,
        will not raise exceptions when any manager has no related domains.
        """
        for mgr in self.list():
            try:
                mgr.sync(default_service_name=default_service_name)
            except EmptyAppIngressError:
                pass

    def safe_update_target(self, service_name: str, service_port_name: str) -> UpdateTargetResult:
        """Update service target for all types of ingress, won't raise exception when ingress
        resource was not found——which might happen when Ingress resource is missing.

        For eg, if `cluster.ingress_config.sub_path_domains` was absent, the Ingress object
        for `SubPathAppIngressMgr` will never be created.

        :return: A result object with "num_of_successful" and "num_of_nonexistent" fields
        """
        num_of_successful, num_of_nonexistent = 0, 0
        for mgr in self.list():
            try:
                mgr.update_target(service_name, service_port_name)
            except AppEntityNotFound:
                logger.info('Ingress resource not found, skip updating target, manager: %s', mgr)
                num_of_nonexistent += 1
                continue
            else:
                num_of_successful += 1
        return UpdateTargetResult(num_of_successful, num_of_nonexistent)

    def delete_if_service_matches(self, service_name: str):
        """Delete all ingress resources if service name matches,
        will not raise exception when ingress resource was not found.
        """
        for mgr in self.list():
            try:
                legacy_ingress = mgr.get()
            except AppEntityNotFound:
                return

            # Only remove ingress when the service_name matches
            if legacy_ingress.service_name == service_name:
                mgr.delete()


class LegacyAppIngressMgr(AppIngressMgr):
    """manage the default legacy default ingress resource"""

    def make_ingress_name(self) -> str:
        return f'{self.app.region}-{self.app.scheduler_safe_name}'

    def list_desired_domains(self) -> List[PIngressDomain]:
        """List all desired domains for current app"""
        # The legacy default host
        cluster = get_cluster_by_app(self.app)
        domain_tmpl = cluster.ingress_config.default_ingress_domain_tmpl
        if not domain_tmpl:
            return []

        # Only write default ingress when `default_ingress_domain_tmpl` was not empty
        default_host = domain_tmpl % self.app.scheduler_safe_name_with_region
        return [PIngressDomain(host=default_host)]
