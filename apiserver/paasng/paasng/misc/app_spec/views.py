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

import typing
from collections import OrderedDict

import yaml
from django.http import HttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from yaml.scanner import ScannerError

from paasng.infras.accounts.permissions.application import application_perm_class
from paasng.infras.iam.permissions.resources.application import AppAction
from paasng.utils.error_codes import error_codes

from .serializers import FileUploadSLZ
from .service import transform_spec2_to_spec3

if typing.TYPE_CHECKING:
    from rest_framework.request import Request


class IndentDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(IndentDumper, self).increase_indent(flow, False)


class AppSpecVersionTransformApiView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated, application_perm_class(AppAction.BASIC_DEVELOP)]

    @swagger_auto_schema(
        request_body=FileUploadSLZ,
        operation_description="Upload a file",
        tags=["应用描述文件版本转换"],
    )
    def post(self, request: "Request"):
        try:
            serializer = FileUploadSLZ(data=request.FILES)
            serializer.is_valid(raise_exception=True)
            spec2_data = yaml.safe_load(serializer.validated_data["file"])
        except ScannerError:
            raise error_codes.NOT_YAML_FILE

        spec3_data = transform_spec2_to_spec3(spec2_data)

        yaml.add_representer(OrderedDict, lambda dumper, data: dumper.represent_dict(data.items()))
        output_yaml = yaml.dump(
            spec3_data, Dumper=IndentDumper, default_flow_style=False, allow_unicode=True, sort_keys=False, indent=2
        )

        response = HttpResponse(output_yaml, content_type="application/x-yaml")
        response["Content-Disposition"] = 'attachment; filename="app_sepc_3.yaml"'
        return response
