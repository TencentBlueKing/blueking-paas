# -*- coding: utf-8 -*-
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
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, ListModelMixin, UpdateModelMixin
from rest_framework.viewsets import GenericViewSet

from paasng.dev_resources.templates.constants import TemplateType
from paasng.dev_resources.templates.models import Template
from paasng.plat_admin.admin42.serializers.templates import TemplateSLZ
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView
from paasng.platform.applications.constants import AppLanguage


class TemplateManageView(GenericTemplateView):
    """平台服务管理-模板配置"""

    template_name = "admin42/configuration/templates.html"
    queryset = Template.objects.all()
    serializer_class = TemplateSLZ
    name = "模板配置"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs.update(
            {'type_choices': dict(TemplateType.get_choices()), 'language_choices': dict(AppLanguage.get_choices())}
        )
        return kwargs


class TemplateViewSet(CreateModelMixin, DestroyModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    """平台服务管理-模板配置API"""

    queryset = Template.objects.all()
    serializer_class = TemplateSLZ
