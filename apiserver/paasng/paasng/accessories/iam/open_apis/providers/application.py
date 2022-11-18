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
from typing import Any, Dict, List, Optional

from django.db.models import Q
from iam.collection import FancyDict
from iam.resource.provider import ListResult, ResourceProvider
from iam.resource.utils import Page

from paasng.accessories.iam.client import BKIAMClient
from paasng.accessories.iam.members.models import ApplicationGradeManager
from paasng.platform.applications.models import Application


class ApplicationProvider(ResourceProvider):
    """蓝鲸应用 Provider"""

    def list_instance(self, filter_obj: FancyDict, page_obj: Page, **options) -> ListResult:
        name_field = self._get_name_field(options.get('language'))
        applications = Application.objects.all().values('code', name_field)
        results = [
            {'id': app['code'], 'display_name': f"{app[name_field]} ({app['code']})"}
            for app in applications[page_obj.slice_from : page_obj.slice_to]
        ]
        return ListResult(results=results, count=applications.count())

    def fetch_instance_info(self, filter_obj: FancyDict, **options) -> ListResult:
        ids = filter_obj.ids or []
        name_field = self._get_name_field(options.get('language'))

        results = []
        applications = Application.objects.filter(code__in=ids)
        approvers = self._fetch_application_approvers([app.code for app in applications])
        for app in applications:
            results.append(
                {
                    'id': app.code,
                    'display_name': f"{getattr(app, name_field)} ({app.code})",
                    '_bk_iam_approver_': approvers[app.code],
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
        keyword = filter_obj.keyword or ''
        name_field = self._get_name_field(options.get('language'))
        applications = Application.objects.filter(
            Q(name__icontains=keyword) | Q(name_en__icontains=keyword) | Q(code__icontains=keyword)
        ).values('code', name_field)
        results = [
            {'id': app['code'], 'display_name': f"{app[name_field]} ({app['code']})"}
            for app in applications[page_obj.slice_from : page_obj.slice_to]
        ]
        return ListResult(results=results, count=applications.count())

    @staticmethod
    def _get_name_field(language: Optional[Any]) -> str:
        return 'name_en' if language == "en" else 'name'

    @staticmethod
    def _fetch_application_approvers(app_codes: List[str]) -> Dict[str, List[str]]:
        """
        获取应用审批人信息（每个应用的分级管理员）

        :param app_codes: 蓝鲸应用 ID 列表
        :returns: 审批人信息，格式：{app_code: single_app_approvers}
        """
        cli = BKIAMClient()
        return {
            m.app_code: cli.fetch_grade_manager_members(m.grade_manager_id)
            for m in ApplicationGradeManager.objects.filter(app_code__in=app_codes)
        }
