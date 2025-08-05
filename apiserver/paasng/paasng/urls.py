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

from django.urls import include, path
from django.views import i18n as django_i18n_views

from paasng.utils.basic import re_path
from paasng.utils.serializers import patch_datetime_field

patch_datetime_field()

urlpatterns = [
    re_path(r"^", include("paasng.misc.metrics.urls")),
    re_path(r"^", include("paasng.misc.plat_config.urls")),
    re_path(r"^", include("paasng.infras.accounts.urls")),
    re_path(r"^", include("paasng.platform.applications.urls")),
    re_path(r"^", include("paasng.accessories.log.urls")),
    re_path(r"^", include("paasng.platform.modules.urls")),
    re_path(r"^", include("paasng.core.region.urls")),
    re_path(r"^", include("paasng.core.tenant.urls")),
    re_path(r"^", include("paasng.misc.audit.urls")),
    re_path(r"^", include("paasng.platform.environments.urls")),
    re_path(r"^", include("paasng.platform.engine.urls")),
    re_path(r"^", include("paasng.platform.engine.processes.urls")),
    re_path(r"^", include("paasng.accessories.ci.urls")),
    re_path(r"^", include("paasng.platform.bkapp_model.urls")),
    re_path(r"^", include("paasng.platform.engine.streaming.urls")),
    re_path(r"^", include("paasng.platform.sourcectl.urls")),
    re_path(r"^", include("paasng.accessories.servicehub.urls")),
    re_path(r"^", include("paasng.accessories.cloudapi.urls")),
    re_path(r"^", include("paasng.accessories.cloudapi_v2.urls")),
    re_path(r"^", include("paasng.bk_plugins.bk_plugins.urls")),
    re_path(r"^", include("paasng.platform.templates.urls")),
    re_path(r"^", include("paasng.platform.smart_app.urls")),
    re_path(r"^", include("paasng.plat_admin.api_doc.urls")),
    re_path(r"^", include("paasng.plat_mgt.urls")),
    re_path(r"^", include("paasng.accessories.publish.market.urls")),
    re_path(r"^", include("paasng.accessories.publish.sync_market.urls")),
    re_path(r"^", include("paasng.accessories.publish.entrance.urls")),
    re_path(r"^", include("paasng.accessories.urls")),
    re_path(r"^", include("paasng.infras.iam.open_apis.urls")),
    re_path(r"^", include("paasng.misc.search.urls")),
    re_path(r"^", include("paasng.misc.monitoring.healthz.urls")),
    re_path(r"^", include("paasng.misc.monitoring.monitor.urls")),
    re_path(r"^", include("paasng.plat_admin.system.urls")),
    re_path(r"^", include("paasng.platform.bk_lesscode.urls")),
    re_path(r"^", include("paasng.platform.evaluation.urls")),
    re_path(r"^", include("paasng.bk_plugins.pluginscenter.urls")),
    re_path(r"^", include("paasng.bk_plugins.pluginscenter.itsm_adaptor.open_apis.urls")),
    re_path(r"^", include("paasng.accessories.app_secret.urls")),
    re_path(r"^", include("paasng.misc.tools.urls")),
    re_path("^", include("paasng.accessories.proc_components.urls")),
    re_path(r"^", include("paasng.misc.ai_agent.urls")),
    # PaaS Admin system
    re_path(r"^admin42/", include("paasng.plat_admin.admin42.urls")),
    re_path(r"^admin42/", include("paas_wl.apis.admin.urls")),
    # switch language
    re_path(r"^i18n/setlang/$", django_i18n_views.set_language, name="set_language"),
    path("", include("paasng.misc.changelog.urls")),
    # Views in paas_wl module
    path("", include("paas_wl.workloads.networking.entrance.urls")),
    path("", include("paas_wl.workloads.networking.egress.urls")),
    path("", include("paas_wl.workloads.networking.ingress.urls")),
    path("", include("paas_wl.workloads.images.urls")),
    path("", include("paas_wl.bk_app.processes.urls")),
    path("", include("paas_wl.bk_app.cnative.specs.urls")),
    path("", include("paasng.accessories.paas_analysis.urls")),
    path("", include("paasng.accessories.dev_sandbox.urls")),
    path("", include("paasng.bk_plugins.pluginscenter.sys_apis.urls")),
    re_path(r"^notice/", include(("bk_notice_sdk.urls", "notice"), namespace="notice")),
]
