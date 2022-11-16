"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from bkpaas_auth.core.constants import ProviderType
from bkpaas_auth.core.encoder import user_id_encoder
from django.conf import settings
from django_filters import CharFilter
from django_filters.rest_framework import FilterSet
from rest_framework.filters import BaseFilterBackend

from paasng.pluginscenter.iam_adaptor.policy.client import lazy_iam_client
from paasng.pluginscenter.models import PluginInstance, PluginRelease


class PluginInstancePermissionFilter(BaseFilterBackend):
    """PluginPermissionFilter will filter those PluginInstance own by the request.user"""

    def filter_queryset(self, request, queryset, view):
        # skip filter if queryset is not for PluginInstance
        if queryset.model is not PluginInstance:
            return queryset
        filters = lazy_iam_client.build_plugin_filters(username=request.user.username)
        if filters:
            return queryset.filter(filters)
        else:
            return queryset.none()


class PluginReleaseFilter(FilterSet):
    creator = CharFilter(method='creator_filter')
    status = CharFilter(field_name="status")

    class Meta:
        model = PluginRelease
        fields = ['creator', 'status']

    def creator_filter(self, queryset, name, value):
        return queryset.filter(
            **{
                "creator": user_id_encoder.encode(getattr(ProviderType, settings.BKAUTH_DEFAULT_PROVIDER_TYPE), value),
            }
        )
