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
from django.conf import settings
from django.utils.functional import SimpleLazyObject
from iam import IAM
from iam.contrib.django.dispatcher import DjangoBasicResourceApiDispatcher
from rest_framework.views import APIView

from paasng.pluginscenter.iam_adaptor.constants import ResourceType
from paasng.pluginscenter.iam_adaptor.management.providers import PluginProvider


def get_api_dispatcher():
    dispatcher = DjangoBasicResourceApiDispatcher(lazy_iam, settings.IAM_PLUGINS_CENTER_SYSTEM_ID)
    dispatcher.register(ResourceType.PLUGIN, PluginProvider())
    return dispatcher


def get_iam():
    return IAM(
        settings.IAM_APP_CODE,
        settings.IAM_APP_SECRET,
        settings.BK_IAM_V3_INNER_URL,
        settings.BKPAAS_URL,
        settings.BK_IAM_APIGATEWAY_URL,
    )


lazy_iam: IAM = SimpleLazyObject(get_iam)  # type: ignore
lazy_api_dispatcher: DjangoBasicResourceApiDispatcher = SimpleLazyObject(get_api_dispatcher)  # type: ignore


class PluginSelectionView(APIView):
    """A view provider IAM resource selection callback for Blueking Plugin"""

    permission_classes = []  # type: ignore

    def post(self, request):
        return lazy_api_dispatcher.as_view()(request)
