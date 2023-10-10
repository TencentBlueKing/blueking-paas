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

from django.views.generic import TemplateView
from rest_framework.generics import GenericAPIView
from rest_framework.pagination import LimitOffsetPagination

from paasng.infras.accounts.permissions.constants import SiteAction
from paasng.infras.accounts.permissions.global_site import site_perm_required


class RetrieveModelMixin:
    """
    Retrieve a model instance.
    """

    def retrieve(self: GenericAPIView, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return serializer.data


class ListModelMixin:
    """
    List model instances.
    """

    def list(self: GenericAPIView, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        serializer = self.get_serializer(page or queryset, many=True)
        return serializer.data


class PaginationMixin:
    """获取分页上下文的mixin"""

    def get_pagination_context(self: GenericAPIView, request):
        if isinstance(self.paginator, LimitOffsetPagination):
            return {
                'count': self.paginator.count,
                'limit': self.paginator.limit,
                'next': self.paginator.get_next_link(),
                'previous': self.paginator.get_previous_link(),
                'curPage': (self.paginator.get_offset(request) // self.paginator.limit) + 1,
            }
        raise NotImplementedError


class GenericTemplateView(TemplateView, RetrieveModelMixin, ListModelMixin, PaginationMixin, GenericAPIView):
    """一个继承了 DRF GenericAPIView 的模板视图, 支持通过 list、retrieve 等方法获取序列化后的对象"""

    schema = None

    @site_perm_required(SiteAction.VISIT_ADMIN42)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    http_method_names = ['get']
