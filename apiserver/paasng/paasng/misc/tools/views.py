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
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from paasng.platform.declarative.application.resources import ApplicationDesc
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.handlers import get_desc_handler
from paasng.platform.smart_app.services.detector import SourcePackageStatReader
from paasng.platform.smart_app.services.prepared import PreparedSourcePackage
from paasng.platform.sourcectl.utils import generate_temp_dir
from paasng.utils.error_codes import error_codes
from paasng.utils.views import get_filepath
from paasng.utils.yaml import IndentDumper

from .app_desc import transform_app_desc_spec2_to_spec3
from .serializers import AppDescSpec2Serializer, ToolPackageStashInputSLZ, ToolPackageStashOutputSLZ


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


class SMartBuilderViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=ToolPackageStashInputSLZ,
        response_serializer=ToolPackageStashOutputSLZ,
        tags=["S-Mart 包构建"],
    )
    def upload(self, request):
        """上传一个待构建的源码包，校验通过后将其暂存起来"""
        slz = ToolPackageStashInputSLZ(data=request.data)
        slz.is_valid(raise_exception=True)

        with generate_temp_dir() as tmp_dir:
            filepath = get_filepath(slz.validated_data["package"], str(tmp_dir))
            stat = SourcePackageStatReader(filepath).read()

            if not stat.meta_info:
                raise error_codes.MISSING_DESCRIPTION_INFO.f(_("解压后未找到 app_desc.yaml 文件"))

            if stat.relative_path != "./":
                raise error_codes.MISSING_DESCRIPTION_INFO.f(_("解压后未在根目录下找到 app_desc.yaml 文件"))

            try:
                app_desc = get_desc_handler(stat.meta_info).app_desc
                self._validate_app_desc(app_desc)
            except DescriptionValidationError as e:
                raise error_codes.FAILED_TO_HANDLE_APP_DESC.f(str(e))

            if not stat.version:
                raise error_codes.MISSING_VERSION_INFO.f(_("app_desc.yaml 中缺少了 app version 信息"))

            # Store as prepared package for later build
            PreparedSourcePackage(request, namespace=self._get_store_namespace(app_desc.code)).store(filepath)

        return Response(ToolPackageStashOutputSLZ({"signature": stat.sha256_signature}).data)

    @staticmethod
    def _validate_app_desc(app_desc: ApplicationDesc):
        # TODO 增加一些前置校验, 确保 app_desc 符合构建要求
        if app_desc.market is None:
            raise DescriptionValidationError({"market": "内容不能为空"})

    @staticmethod
    def _get_store_namespace(app_code: str) -> str:
        return f"{app_code}:prepared_build"
