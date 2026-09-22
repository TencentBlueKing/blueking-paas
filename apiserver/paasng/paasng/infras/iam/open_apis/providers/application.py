# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from typing import Any, Dict, List, Optional

from django.db.models import Q
from iam.collection import FancyDict
from iam.resource.provider import ListResult, ResourceProvider
from iam.resource.utils import Page

from paasng.infras.iam.members.models import ApplicationGradeManager
from paasng.infras.iam.shim import get_management_backend
from paasng.platform.applications.models import Application
from paasng.platform.applications.tenant import get_tenant_id_for_app


class ApplicationProvider(ResourceProvider):
    """蓝鲸应用 Provider"""

    def list_instance(self, filter_obj: FancyDict, page_obj: Page, **options) -> ListResult:
        name_field = self._get_name_field(options.get("language"))
        applications = Application.objects.filter(tenant_id=options["tenant_id"]).values("code", name_field)
        results = [
            {"id": app["code"], "display_name": f"{app[name_field]} ({app['code']})"}
            for app in applications[page_obj.slice_from : page_obj.slice_to]
        ]
        return ListResult(results=results, count=applications.count())

    def fetch_instance_info(self, filter_obj: FancyDict, **options) -> ListResult:
        ids = filter_obj.ids or []
        name_field = self._get_name_field(options.get("language"))

        results = []
        applications = Application.objects.filter(code__in=ids, tenant_id=options["tenant_id"])
        approvers = self._fetch_application_approvers([app.code for app in applications])
        for app in applications:
            results.append(
                {
                    "id": app.code,
                    "display_name": f"{getattr(app, name_field)} ({app.code})",
                    "_bk_iam_approver_": approvers[app.code],
                }
            )

        return ListResult(results=results, count=len(results))

    def list_instance_by_policy(self, filter_obj: FancyDict, page_obj: Page, **options) -> ListResult:
        return ListResult(results=[], count=0)

    def list_attr(self, **options) -> ListResult:
        return ListResult(results=[], count=0)

    def list_attr_value(self, filter_obj: FancyDict, page_obj: Page, **options) -> ListResult:
        return ListResult(results=[], count=0)

    def search_instance(self, filter_obj: FancyDict, page_obj: Page, **options) -> ListResult:
        """支持模糊搜索应用名"""
        keyword = filter_obj.keyword or ""
        name_field = self._get_name_field(options.get("language"))
        applications = (
            Application.objects.filter(tenant_id=options["tenant_id"])
            .filter(Q(name__icontains=keyword) | Q(name_en__icontains=keyword) | Q(code__icontains=keyword))
            .values("code", name_field)
        )
        results = [
            {"id": app["code"], "display_name": f"{app[name_field]} ({app['code']})"}
            for app in applications[page_obj.slice_from : page_obj.slice_to]
        ]
        return ListResult(results=results, count=applications.count())

    @staticmethod
    def _get_name_field(language: Optional[Any]) -> str:
        return "name_en" if language == "en" else "name"

    @staticmethod
    def _fetch_application_approvers(app_codes: List[str]) -> Dict[str, List[str]]:
        """获取应用审批人（V3 分级管理员成员 / V4 管理空间管理员）

        必须走 `get_management_backend`，不能直连 V3 的 `BKIAMClient`：V4 环境里
        `grade_manager_id` 存的是管理空间 ID，打 V3 的 grade_managers 接口会被 403。
        """
        return {
            m.app_code: get_management_backend(get_tenant_id_for_app(m.app_code)).fetch_management_space_members(
                m.grade_manager_id
            )
            for m in ApplicationGradeManager.objects.filter(app_code__in=app_codes)
        }
