# -*- coding: utf-8 -*-
from rest_framework.pagination import LimitOffsetPagination


class PaginationMixin:
    """获取分页上下文的mixin"""

    paginator: LimitOffsetPagination

    def get_pagination_context(self, request):
        if isinstance(self.paginator, LimitOffsetPagination):
            return {
                'count': self.paginator.count,
                'limit': self.paginator.limit,
                'next': self.paginator.get_next_link(),
                'previous': self.paginator.get_previous_link(),
                'curPage': (self.paginator.get_offset(request) // self.paginator.limit) + 1,
            }
        raise NotImplementedError
