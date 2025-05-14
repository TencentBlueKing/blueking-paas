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

from functools import reduce
from operator import or_

from django.db.models import Q
from iam.resource.provider import ListResult, ResourceProvider
from iam.resource.utils import FancyDict, Page

from paasng.bk_plugins.pluginscenter.iam_adaptor.definitions import gen_iam_resource_id, gen_iam_resource_name
from paasng.bk_plugins.pluginscenter.iam_adaptor.management.shim import fetch_grade_manager_members
from paasng.bk_plugins.pluginscenter.models import PluginInstance


class PluginProvider(ResourceProvider):
    """IAM ResourceProvider implement for Blueking Plugin"""

    def list_attr(self, **options):
        return ListResult(results=[], count=0)

    def list_attr_value(self, filter: FancyDict, page: Page, **options):
        return ListResult(results=[], count=0)

    def list_instance(self, filter: FancyDict, page: Page, **options):
        qs = PluginInstance.objects.all().order_by("created")
        paginated_qs = qs[page.slice_from : page.slice_to]
        results = [
            {"id": gen_iam_resource_id(plugin), "display_name": gen_iam_resource_name(plugin)}
            for plugin in paginated_qs
        ]
        return ListResult(results=results, count=qs.count())

    def fetch_instance_info(self, filter: FancyDict, **options):
        ids = filter.ids or []
        results = []
        for resource_id in ids:
            pd_id, plugin_id = resource_id.split(":")
            plugin = PluginInstance.objects.get(pd__identifier=pd_id, id=plugin_id)
            results.append(
                {
                    "id": gen_iam_resource_id(plugin),
                    "display_name": gen_iam_resource_name(plugin),
                    "_bk_iam_approver_": fetch_grade_manager_members(plugin),
                }
            )
        return ListResult(results=results, count=len(results))

    def list_instance_by_policy(self, filter, page, **options):
        return ListResult(results=[], count=0)

    def search_instance(self, filter: FancyDict, page: Page, **options):
        """支持模糊搜索插件"""
        keyword = filter.keyword or ""
        search_fields = ["name_zh_cn", "name_en", "id"]
        orm_lookups = [self.construct_search(str(search_field)) for search_field in search_fields]
        queries = [Q(**{orm_lookup: keyword}) for orm_lookup in orm_lookups]
        qs = PluginInstance.objects.filter(reduce(or_, queries)).all()
        paginated_qs = qs[page.slice_from : page.slice_to]
        results = [
            {"id": gen_iam_resource_id(plugin), "display_name": gen_iam_resource_name(plugin)}
            for plugin in paginated_qs
        ]
        return ListResult(results=results, count=qs.count())
