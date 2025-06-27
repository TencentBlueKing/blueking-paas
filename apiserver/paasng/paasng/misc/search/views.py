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

from django.utils.functional import cached_property
from drf_yasg.utils import swagger_auto_schema
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from paasng.accessories.publish.entrance.exposer import get_exposed_links
from paasng.platform.applications.models import UserApplicationFilter

from .backends import BKDocumentSearcher, MixSearcher
from .serializers import AppSearchResultSLZ, DocSearchResultSLZ, DocumentSearchWordSLZ, DocumentSLZ, UniversalSearchSLZ


class MixDocumentSearch(ViewSet):
    @swagger_auto_schema(
        operation_id="api-mix-doc-search", responses={200: DocumentSLZ}, query_serializer=DocumentSearchWordSLZ
    )
    def search(self, request, format=None):
        """
        :return:
            [
                {
                    "url": "/xxx/xxx",
                    "title": "xxxx"
                },
            ]
        """
        slz = DocumentSearchWordSLZ(data=request.GET)
        slz.is_valid(raise_exception=True)
        keyword = slz.validated_data["keyword"]
        return Response(MixSearcher().search(keyword))


class ApplicationsSearchViewset(ViewSet):
    @cached_property
    def paginator(self):
        """Return a pagination object with a small default limit"""
        _paginator = LimitOffsetPagination()
        _paginator.default_limit = 10
        return _paginator

    @swagger_auto_schema(
        # Use serializer with only "keyword" field to avoid conflict
        operation_id="api-application-search",
        query_serializer=DocumentSearchWordSLZ,
        tags=["搜索"],
        responses={200: AppSearchResultSLZ(many=True)},
    )
    def search(self, request):
        """搜索应用，返回类似于应用列表页的详细结果"""

        slz = UniversalSearchSLZ(data=request.GET)
        slz.is_valid(raise_exception=True)

        applications = UserApplicationFilter(request.user).filter(order_by=["name"], search_term=slz.data["keyword"])
        paged_applications = self.paginator.paginate_queryset(applications, self.request, view=self)
        # Set exposed links property, to be used by the serializer later
        for app in paged_applications:
            app._deploy_info = get_exposed_links(app)
        return Response(AppSearchResultSLZ({"results": paged_applications, "count": applications.count()}).data)


class BkDocsSearchViewset(ViewSet):
    @swagger_auto_schema(
        operation_id="api-bkdoc-search",
        query_serializer=UniversalSearchSLZ,
        tags=["搜索"],
        responses={200: DocSearchResultSLZ(many=True)},
    )
    def search(self, request):
        """搜索蓝鲸资料库，返回资料库中文档条目。

        该接口返回的条目没有“摘要“、”作者“、”最近更新“字段，只展示标题。
        """
        slz = UniversalSearchSLZ(data=request.GET)
        slz.is_valid(raise_exception=True)
        results = BKDocumentSearcher().search(keyword=slz.data["keyword"])

        # Slice search results
        start = slz.data["offset"]
        stop = slz.data["offset"] + slz.data["limit"]
        docs = results.docs[start:stop]
        return Response(DocSearchResultSLZ({"results": docs, "count": results.count}).data)
