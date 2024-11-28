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

from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.utils.yaml import IndentDumper

from .app_desc import transform_app_desc_spec2_to_spec3


def validate_spec2(spec2):
    """
    Validates the spec_version 2 application description.

    :param spec2: Application description in spec_version 2 format.
    :type spec2: dict
    :raises ValueError: If required fields are missing or data is invalid.
    :raises TypeError: If data type is invalid.
    """
    if not isinstance(spec2, dict):
        raise TypeError("The input data must be a dictionary.")

    if spec2.get("spec_version") != 2:
        raise ValueError("'spec_version' must be 2.")

    if "app" in spec2 and not isinstance(spec2.get("app"), dict):
        raise TypeError("'app' must be a dictionary if present in the input data.")

    if "modules" not in spec2 and "module" not in spec2:
        raise ValueError("Either 'modules' or 'module' must be present in the input data.")

    if "modules" in spec2 and not isinstance(spec2.get("modules"), dict):
        raise TypeError("'modules' must be a dictionary if present in the input data.")

    if "modules" in spec2 and not isinstance(spec2.get("modules"), dict):
        raise TypeError("'module' must be a dictionary if present in the input data.")


class AppDescTransformAPIView(APIView):
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(
        tags=["应用描述文件版本转换"],
    )
    def post(self, request):
        if request.content_type != "application/yaml":
            return HttpResponseBadRequest("Invalid content type: only application/yaml is allowed")

        yaml_data = request.body.decode(settings.DEFAULT_CHARSET)
        if not yaml_data.strip():
            return HttpResponse()

        try:
            spec2_data = yaml.safe_load(yaml_data)
        except yaml.YAMLError as e:
            return HttpResponseBadRequest(f"Error parsing YAML content: {str(e)}")

        try:
            validate_spec2(spec2_data)
        except (ValueError, TypeError) as e:
            return HttpResponseBadRequest(str(e))

        spec3_data = transform_app_desc_spec2_to_spec3(spec2_data)

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

        response = HttpResponse(output_yaml, content_type="application/yaml")
        return response
