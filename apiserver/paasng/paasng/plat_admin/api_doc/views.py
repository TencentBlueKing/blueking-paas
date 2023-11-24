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
from typing import Dict

import yaml
from django.conf import settings
from django.template.loader import get_template
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework.response import Response

from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_class

schema_view = get_schema_view(
    openapi.Info(
        title="PaaS V3 API",
        default_version="vx",
        description="PaaS V3 API Document",
        terms_of_service=settings.BKPAAS_URL,
        contact=openapi.Contact(email="blueking@tencent.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=False,
    permission_classes=(site_perm_class(SiteAction.VISIT_ADMIN42),),
)


class FullSwaggerConfigurationView(schema_view):  # type: ignore
    """A swagger view base on auto generate docs, and merged the hand-write swagger docs"""

    def get(self, request):
        auto_gen_resp = super().get(request)
        default = auto_gen_resp.data

        # docs write at swagger.yaml
        swagger_file = yaml.safe_load(get_template("api/swagger.yaml").render())
        self._merge_paths(default, swagger_file)
        self._merge_definitions(default, swagger_file)

        return Response(default)

    def _merge_paths(self, base: Dict, target: Dict, base_path: str = "", ignore_conflict: bool = True):
        """合并 swagger docs 中的 paths 字段"""
        to_merge = target.get("paths")
        if not isinstance(to_merge, dict):
            return
        for raw_key, sub_item in to_merge.items():
            sub_key = base_path + raw_key
            if sub_key in base["paths"]:
                if ignore_conflict:
                    continue
                raise Exception(f"paths conflict at f`{sub_key}`")
            base["paths"][sub_key] = sub_item

    def _merge_definitions(self, base: Dict, target: Dict, ignore_conflict: bool = True):
        """合并 swagger docs 中的 definitions 字段"""
        to_merge = target.get("definitions")
        if not isinstance(to_merge, dict):
            return
        for sub_key, sub_item in to_merge.items():
            if sub_key in base["definitions"]:
                if ignore_conflict:
                    continue
                raise Exception(f"definitions conflict at f`{sub_key}`")
            base["definitions"][sub_key] = sub_item
