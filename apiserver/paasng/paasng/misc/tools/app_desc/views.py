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

from collections import OrderedDict

import yaml
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from paasng.utils.yaml import IndentDumper

from .app_desc import transform_app_desc_spec2_to_spec3
from .serializers import AppDescSpec2Serializer


class AppDescTransformAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["应用描述文件版本转换"],
    )
    def post(self, request):
        if request.content_type != "application/yaml":
            return HttpResponseBadRequest("Invalid content type: only application/yaml is allowed")

        yaml_data = request.body.decode(settings.DEFAULT_CHARSET)

        try:
            spec2_data = yaml.safe_load(yaml_data)
        except yaml.YAMLError as e:
            return HttpResponseBadRequest(f"Error parsing YAML content: {str(e)}")

        serializer = AppDescSpec2Serializer(data=spec2_data)
        serializer.is_valid(raise_exception=True)

        try:
            spec3_data = transform_app_desc_spec2_to_spec3(serializer.validated_data)
        except Exception as e:
            return HttpResponseBadRequest(f"Error occurred during transformation: {str(e)}")

        try:
            yaml.add_representer(OrderedDict, lambda dumper, data: dumper.represent_dict(data.items()))
            output_yaml = yaml.dump(
                spec3_data,
                Dumper=IndentDumper,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
                indent=2,
                width=1000,
            )
        except yaml.YAMLError as e:
            return HttpResponseBadRequest(f"Error generating YAML output: {str(e)}")

        return HttpResponse(output_yaml, content_type="application/yaml")
