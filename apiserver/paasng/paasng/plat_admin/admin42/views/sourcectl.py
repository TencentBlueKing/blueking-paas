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
from django.conf import settings
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, ListModelMixin, UpdateModelMixin
from rest_framework.viewsets import GenericViewSet

from paasng.dev_resources.sourcectl.models import SourceTypeSpecConfig
from paasng.plat_admin.admin42.serializers.sourcectl import SourceTypeSpecConfigSLZ
from paasng.plat_admin.admin42.utils.mixins import GenericTemplateView
from paasng.publish.entrance.exposer import get_bk_doc_url_prefix


class SourceTypeSpecManageView(GenericTemplateView):
    """平台服务管理-代码库配置"""

    template_name = "admin42/platformmgr/sourcectl.html"
    queryset = SourceTypeSpecConfig.objects.all()
    serializer_class = SourceTypeSpecConfigSLZ
    name = "代码库配置"

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)

        available_spec_cls = [
            'BkSvnSourceTypeSpec',
            'GitHubSourceTypeSpec',
            'GiteeSourceTypeSpec',
            'BareGitSourceTypeSpec',
            'BareSvnSourceTypeSpec',
            'GitLabSourceTypeSpec',
        ]
        # 存在 TcGitSourceTypeSpec 才将其添加到可选项中
        try:
            from paasng.dev_resources.sourcectl.type_specs import TcGitSourceTypeSpec  # noqa

            available_spec_cls.append('TcGitSourceTypeSpec')
        except ImportError:
            pass

        kwargs.update(
            {
                'bk_docs_url_prefix': get_bk_doc_url_prefix(),
                'bk_paas_url': settings.BKPAAS_URL,
                'spec_cls_choices': {
                    f'paasng.dev_resources.sourcectl.type_specs.{spec_cls}': spec_cls
                    for spec_cls in available_spec_cls
                },
            }
        )
        return kwargs


class SourceTypeSpecViewSet(CreateModelMixin, DestroyModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    """平台服务管理-代码库配置API"""

    queryset = SourceTypeSpecConfig.objects.all()
    serializer_class = SourceTypeSpecConfigSLZ
