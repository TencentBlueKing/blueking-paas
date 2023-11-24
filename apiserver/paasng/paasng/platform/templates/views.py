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
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.response import Response

from paasng.platform.engine.configurations.image import get_image_repository_template
from paasng.platform.engine.constants import RuntimeType
from paasng.platform.templates.exceptions import TmplRegionNotSupported
from paasng.platform.templates.manager import TemplateRuntimeManager, retrieve_template_build_config
from paasng.platform.templates.models import Template
from paasng.platform.templates.serializers import SearchTemplateSLZ, TemplateDetailSLZ, TemplateSLZ
from paasng.utils.error_codes import error_codes


class TemplateViewSet(viewsets.ViewSet):
    def list_tmpls(self, request, tpl_type):
        """获取指定 region、类型的模板列表"""
        slz = SearchTemplateSLZ(data=request.query_params)
        slz.is_valid(raise_exception=True)

        params = slz.validated_data
        tmpls = Template.objects.filter_by_region(region=params["region"], type=tpl_type)
        return Response(TemplateSLZ(tmpls, many=True).data)


class RegionTemplateViewSet(viewsets.ViewSet):
    @swagger_auto_schema(response_serializer=TemplateSLZ(many=True))
    def list(self, request, tpl_type, region):
        """获取指定 region、类型的模板列表"""
        tmpls = Template.objects.filter_by_region(region=region, type=tpl_type)
        return Response(TemplateSLZ(tmpls, many=True).data)

    @swagger_auto_schema(response_serializer=TemplateDetailSLZ)
    def retrieve(self, request, tpl_type, region, tpl_name):
        """获取指定模板的详情"""
        try:
            mgr = TemplateRuntimeManager(region=region, tmpl_name=tpl_name)
            build_config = retrieve_template_build_config(region=region, template=mgr.template)
        except (ObjectDoesNotExist, TmplRegionNotSupported):
            raise error_codes.NORMAL_TMPL_NOT_FOUND.f(_("模板名称: {tmpl_name}").format(tmpl_name=tpl_name))

        build_config_data = {
            "image_repository_template": get_image_repository_template(),
            "build_method": build_config.build_method,
            "tag_options": build_config.tag_options,
        }
        if build_config.build_method == RuntimeType.BUILDPACK:
            build_config_data.update(
                bp_stack_name=build_config.buildpack_builder.name,  # type: ignore
                buildpacks=build_config.buildpacks,
            )
        elif build_config.build_method == RuntimeType.DOCKERFILE:
            build_config_data.update(
                dockerfile_path=build_config.dockerfile_path,
                docker_build_args=build_config.docker_build_args,
            )
        else:
            raise error_codes.UNKNOWN_TEMPLATE

        return Response(
            TemplateDetailSLZ(
                {
                    "build_config": build_config_data,
                    "preset_addons": mgr.get_preset_services_config(),
                    "slugbuilder": build_config.buildpack_builder,
                }
            ).data
        )
