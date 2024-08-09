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

"""paasng URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import include, url
from django.urls import path
from django.views import i18n as django_i18n_views

from paasng.utils.serializers import patch_datetime_field

patch_datetime_field()

urlpatterns = [
    path("", include("paasng.misc.metrics.urls")),
    path("", include("paasng.misc.plat_config.urls")),
    url(r"^", include("paasng.infras.accounts.urls")),
    url(r"^", include("paasng.platform.applications.urls")),
    url(r"^", include("paasng.accessories.log.urls")),
    url(r"^", include("paasng.platform.modules.urls")),
    url(r"^", include("paasng.core.region.urls")),
    url(r"^", include("paasng.misc.audit.urls")),
    url(r"^", include("paasng.misc.operations.urls")),
    url(r"^", include("paasng.platform.environments.urls")),
    url(r"^", include("paasng.platform.engine.urls")),
    url(r"^", include("paasng.platform.engine.processes.urls")),
    url(r"^", include("paasng.accessories.ci.urls")),
    url(r"^", include("paasng.platform.bkapp_model.urls")),
    url(r"^", include("paasng.platform.engine.streaming.urls")),
    url(r"^", include("paasng.platform.sourcectl.urls")),
    url(r"^", include("paasng.accessories.servicehub.urls")),
    url(r"^", include("paasng.accessories.cloudapi.urls")),
    url(r"^", include("paasng.bk_plugins.bk_plugins.urls")),
    url(r"^", include("paasng.platform.templates.urls")),
    url(r"^", include("paasng.platform.smart_app.urls")),
    url(r"^", include("paasng.plat_admin.api_doc.urls")),
    url(r"^", include("paasng.accessories.publish.market.urls")),
    url(r"^", include("paasng.accessories.publish.sync_market.urls")),
    url(r"^", include("paasng.accessories.publish.entrance.urls")),
    url(r"^", include("paasng.accessories.urls")),
    url(r"^", include("paasng.infras.iam.open_apis.urls")),
    url(r"^", include("paasng.misc.search.urls")),
    url(r"^", include("paasng.misc.monitoring.healthz.urls")),
    url(r"^", include("paasng.misc.monitoring.monitor.urls")),
    url(r"^", include("paasng.plat_admin.system.urls")),
    url(r"^", include("paasng.platform.bk_lesscode.urls")),
    url(r"^", include("paasng.platform.evaluation.urls")),
    url(r"^", include("paasng.bk_plugins.pluginscenter.urls")),
    url(r"^", include("paasng.bk_plugins.pluginscenter.itsm_adaptor.open_apis.urls")),
    url(r"^", include("paasng.accessories.app_secret.urls")),
    # PaaS Admin system
    url(r"^admin42/", include("paasng.plat_admin.admin42.urls")),
    url(r"^admin42/", include("paas_wl.apis.admin.urls")),
    # switch language
    url(r"^i18n/setlang/$", django_i18n_views.set_language, name="set_language"),
    path("", include("paasng.misc.changelog.urls")),
    # Views in paas_wl module
    path("", include("paas_wl.workloads.networking.entrance.urls")),
    path("", include("paas_wl.workloads.networking.egress.urls")),
    path("", include("paas_wl.workloads.networking.ingress.urls")),
    path("", include("paas_wl.workloads.images.urls")),
    path("", include("paas_wl.bk_app.processes.urls")),
    path("", include("paas_wl.bk_app.cnative.specs.urls")),
    url(r"^", include("paasng.accessories.paas_analysis.urls")),
    url(r"^notice/", include(("bk_notice_sdk.urls", "notice"), namespace="notice")),
    url(r"^", include("paasng.accessories.dev_sandbox.urls")),
]
