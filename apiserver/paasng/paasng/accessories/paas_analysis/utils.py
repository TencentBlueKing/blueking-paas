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
import datetime
from typing import Any, Dict, Tuple

from django.utils.translation import gettext as _

from paas_wl.bk_app.applications.api import get_metadata_by_env, update_metadata_by_env
from paas_wl.workloads.networking.sync import sync_proc_ingresses
from paasng.accessories.paas_analysis import clients
from paasng.accessories.paas_analysis.constants import PAMetadataKey, get_metrics_source_type_from_str
from paasng.accessories.paas_analysis.models import Site
from paasng.platform.applications.models import Application, ModuleEnvironment


def get_pv_uv_for_env(
    env: ModuleEnvironment, start_date: datetime.date, end_date: datetime.date, metric_source_type: str = "ingress"
) -> Tuple[int, int]:
    """
    A shortcut for getting pv/uv from the given env
    :param env: 指定需要统计的环境
    :param start_date: 指定统计 pv/uv 的开始时间(包含)
    :param end_date: 指定统计 pv/uv 的结束时间(包含)
    :param metric_source_type: 指定统计哪个来源的 pv/uv
    :return: pv, uv
    """
    site = get_or_create_site_by_env(env)
    client = clients.SiteMetricsClient(site, get_metrics_source_type_from_str(metric_source_type))
    metric = client.get_total_page_view_metric_about_site(start_time=start_date, end_time=end_date)
    result = metric["result"]["results"]
    return result["pv"], result["uv"]


def get_or_create_site_by_env(env: ModuleEnvironment) -> Site:
    """Get or create a Site object by calling paas-analysis site

    :raises: PAClientException
    """
    site_json = clients.PAClient().get_or_create_app_site(
        app_code=env.application.code,
        module_name=env.module.name,
        env=env.environment,
    )
    return Site(region=env.module.region, **site_json)


def get_or_create_custom_site_for_application(application: Application, site_name: str) -> Site:
    """Get or create a Site object for application

    :raises: PAClientException
    """
    if site_name != "default":
        # NOTE: 增加防御式判断, 当支持用户自定义站点时移除该代码
        raise ValueError(_("目前仅支持以 default 命名的自定义站点"))
    # {app_code}:{module_name}:{site_name}
    name = f"{application.code}:default:{site_name}"
    site_json = clients.PAClient().get_or_create_custom_site(site_name=name)
    return Site(region=application.region, **site_json)


def make_app_metadata(env: ModuleEnvironment) -> Dict[str, Any]:
    """Return an engine app's metadata dict"""
    site = get_or_create_site_by_env(env)
    return {PAMetadataKey.SITE_ID.value: site.id}


def get_ingress_tracking_status(env: ModuleEnvironment) -> bool:
    """Get ingress tracking status by querying metadata. This approach was not really reliable because some apps might
    have correct metadata while it's ingress config was not synced yet.
    """
    return bool(get_metadata_by_env(env).bkpa_site_id)


def enable_ingress_tracking(env: ModuleEnvironment):
    """Enable ingress tracking by injecting a metadata and re-sync ingress configs

    :raises: PAClientException when unable to get or create site object
    """
    # Update metadata and re-sync ingress configs
    # If pa-related metadata already exists, do not proceed
    if get_metadata_by_env(env).bkpa_site_id:
        return

    update_metadata_by_env(env, make_app_metadata(env))
    sync_proc_ingresses(env)
