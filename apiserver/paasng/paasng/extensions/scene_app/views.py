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
from rest_framework import viewsets
from rest_framework.response import Response

from paasng.dev_resources.templates.constants import TemplateType
from paasng.dev_resources.templates.models import Template

from .serializers import ListSceneTmplsSLZ, SceneTmplSLZ


class SceneAppViewSet(viewsets.ViewSet):
    """场景 SaaS 相关 API"""

    def list_tmpls(self, request):
        """获取指定 region 可用场景模板列表"""
        slz = ListSceneTmplsSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)

        params = slz.validated_data
        tmpls = Template.objects.filter_by_region(region=params['region'], type=TemplateType.SCENE)
        return Response(SceneTmplSLZ(tmpls, many=True).data)
