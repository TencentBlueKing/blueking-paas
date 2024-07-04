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

"""Ingress plugins which provide extra server snippet to app's ingress configs"""
import logging
from abc import ABC
from textwrap import dedent
from typing import TYPE_CHECKING, Optional, Sequence

from django.conf import settings

from paas_wl.bk_app.applications.managers import get_metadata
from paas_wl.bk_app.applications.models import WlApp
from paas_wl.workloads.networking.ingress.plugins.exceptions import PluginNotConfigured
from paasng.utils.configs import RegionAwareConfig

if TYPE_CHECKING:
    from paas_wl.workloads.networking.ingress.entities import PIngressDomain

logger = logging.getLogger(__name__)


class IngressPlugin(ABC):
    """Ingress plugin type

    :param app: current WlApp object
    :param domains: current ingress domains objects
    """

    config_key: str

    def __init__(self, app: WlApp, domains: Optional[Sequence["PIngressDomain"]] = None):
        self.app = app
        self.domains = domains

    def make_server_snippet(self) -> str:
        """Make server snippet which will be placed in "server" block

        WARNING: Ingresses may share same host in certain situations, for example:
        when "sub_path_domain" is enabled in a cluster. If multiple server snippets
        were found for a host, only one annotation will be written to the final
        generated nginx config file. Which means you should implement this method
        with caution, prefer "configuration-snippet" if it meets your requirement.
        """
        return ""

    def make_configuration_snippet(self) -> str:
        """Make configuration snippet which will be placed in "location" block"""
        return ""

    def _get_config(self) -> RegionAwareConfig:
        """Get config object from settings"""
        try:
            json_config = settings.SERVICES_PLUGINS[self.config_key]
        except KeyError:
            raise PluginNotConfigured(f"services plugin:{self.config_key} was not configured")
        return RegionAwareConfig(json_config)


class AccessControlPlugin(IngressPlugin):
    """Access control module for ingress

    Config format:

    ```
    {'dj_admin_ip_range_map': 'inner', 'redis_server_name': 'local'}
    ```
    """

    config_key = "access_control"

    TMPL = dedent(
        """\
        # Blow content was configured by access-control plugin, do not edit

        set $bkapp_app_code '{app_name}';
        set $bkapp_bk_app_code '{bk_app_name}';
        set $bkapp_region '{region}';
        set $bkapp_env_name '{env_name}';

        set $acc_redis_server_name '{redis_server_name}';
        set $acc_dj_admin_ip_range '{dj_admin_ip_range}';

        access_by_lua_file $module_access_path/main.lua;

        # content of access-control plugin ends
        """
    )

    def __init__(self, app: WlApp, domains: Optional[Sequence["PIngressDomain"]] = None):
        super().__init__(app, domains)

    def make_configuration_snippet(self) -> str:
        """Configuration snippet for access_control module

        **Different apps may share same host by adopting different subpaths, so
        below snippet must be placed in "location" instead of "server" section or
        config collision will happen.**

        :raises: PluginNotConfigured when not plugin config can be found in settings
        """
        conf = self._get_config().get(self.app.region)
        if not get_metadata(self.app).acl_is_enabled:
            return ""

        # app_name is not the REAL app name, we need to prepend the region field to make
        # access control works
        app_name = self.app.region + "-" + self.app.name

        # In case app's metadata is not available
        default_env_name = self.app.name.rsplit("-", 1)[-1]
        env_name = self.app.latest_config.values.get("environment", default_env_name)

        redis_server_name = conf["redis_server_name"]
        dj_admin_ip_range = conf["dj_admin_ip_range_map"]
        return self.TMPL.format(
            app_name=app_name,
            bk_app_name=get_metadata(self.app).get_paas_app_code(),
            region=self.app.region,
            env_name=env_name,
            redis_server_name=redis_server_name,
            dj_admin_ip_range=dj_admin_ip_range,
        )


class PaasAnalysisPlugin(IngressPlugin):
    """Add paas analysis configs for ingress

    Config format:

    ```
    {'enabled': True}
    ```
    """

    config_key = "paas_analysis"
    TMPL = dedent(
        """\
        set $bkpa_site_id {bkpa_site_id};
        header_filter_by_lua_file $module_root/paas_analysis/main.lua;
        """
    )

    def __init__(self, app: WlApp, domains: Optional[Sequence["PIngressDomain"]] = None):
        super().__init__(app, domains)

    def make_configuration_snippet(self) -> str:
        """configuration snippet for paas_analysis module

        :raises: PluginNotConfigured when no plugin configs can be found in settings
        """
        conf = self._get_config().get(self.app.region)
        if not conf.get("enabled", False):
            return ""

        bkpa_site_id = get_metadata(self.app).bkpa_site_id
        if bkpa_site_id is None:
            logger.warning('"bkpa_site_id" not found in metadata')
            return ""

        return self.TMPL.format(bkpa_site_id=str(bkpa_site_id))


def register():
    """Register default plugins"""
    from paas_wl.workloads.networking.ingress.plugins import register_plugin

    register_plugin(AccessControlPlugin)
    register_plugin(PaasAnalysisPlugin)
