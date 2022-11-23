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
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from paasng.platform.feature_flags.constants import PlatformFeatureFlag


class FeatureFlagViewSet(ViewSet):
    @swagger_auto_schema(tags=["特性标记"])
    def get_features(self, request):
        return Response(PlatformFeatureFlag.get_default_flags())
