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
    path('', include('paasng.metrics.urls')),
    path('', include('paasng.platform.feature_flags.urls')),
    url(r'^', include('paasng.accounts.urls')),
    url(r'^', include('paasng.platform.applications.urls')),
    url(r'^', include('paasng.platform.log.urls')),
    url(r'^', include('paasng.platform.modules.urls')),
    url(r'^', include('paasng.platform.region.urls')),
    url(r'^', include('paasng.platform.operations.urls')),
    url(r'^', include('paasng.platform.environments.urls')),
    url(r'^', include('paasng.engine.urls')),
    url(r'^', include('paasng.engine.processes.urls')),
    url(r'^', include('paasng.ci.urls')),
    url(r'^', include('paasng.engine.streaming.urls')),
    url(r'^', include('paasng.dev_resources.sourcectl.urls')),
    url(r'^', include('paasng.dev_resources.servicehub.urls')),
    url(r'^', include('paasng.dev_resources.cloudapi.urls')),
    url(r'^', include('paasng.extensions.bk_plugins.urls')),
    url(r'^', include('paasng.dev_resources.templates.urls')),
    url(r'^', include('paasng.extensions.smart_app.urls')),
    url(r'^admin42/', include('paasng.plat_admin.admin42.urls')),
    url(r'^', include('paasng.plat_admin.api_doc.urls')),
    url(r'^', include('paasng.publish.market.urls')),
    url(r'^', include('paasng.publish.sync_market.urls')),
    url(r'^', include('paasng.publish.entrance.urls')),
    url(r'^', include('paasng.accessories.urls')),
    url(r'^', include('paasng.accessories.iam.open_apis.urls')),
    url(r'^', include('paasng.accessories.search.urls')),
    url(r'^', include('paasng.monitoring.healthz.urls')),
    url(r'^', include('paasng.monitoring.monitor.urls')),
    url(r'^', include('paasng.plat_admin.system.urls')),
    url(r'^', include('paasng.accessories.bk_lesscode.urls')),
    url(r"^", include('paasng.pluginscenter.urls')),
    # A universal reverse proxy for other services
    url(r'^', include('paasng.service_proxy.urls')),
    # switch language
    url(r'^i18n/setlang/$', django_i18n_views.set_language, name="set_language"),
    path('', include('paasng.accessories.changelog.urls')),
]
