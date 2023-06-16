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
from typing import Dict, Optional

from django.conf import settings
from elasticsearch_dsl import Search
from elasticsearch_dsl.aggs import Agg
from elasticsearch_dsl.query import Q, Query

from paasng.utils.es_log.time_range import SmartTimeRange

pre_tag: str = settings.BK_LOG_HIGHLIGHT_TAG[0]
post_tag: str = settings.BK_LOG_HIGHLIGHT_TAG[1]


class SmartSearch:
    """Proxy to elasticsearch_dsl.Search, will inject time range filter automatically"""

    search: Search

    def __init__(self, time_field: str, time_range: SmartTimeRange):
        self.time_field = time_field
        self.time_range = time_range
        self.search = Search().filter("range", **time_range.get_time_range_filter(time_field))
        self.search = self.search.sort({time_field: {"order": "desc"}})

    def filter(self, *args, **kwargs):
        """add filter to search dsl"""
        self.search = self.search.filter(*args, **kwargs)
        return self

    def exclude(self, *args, **kwargs):
        """add ~filter to search dsl"""
        self.search = self.search.exclude(*args, **kwargs)
        return self

    def limit_offset(self, limit: int = 100, offset: int = 0):
        """page filter by limit and offset"""
        self.search = self.search.extra(size=limit, from_=offset)
        return self

    def query(self, dsl: Query):
        """query by dsl"""
        self.search = self.search.query(dsl)
        return self

    def sort(self, keys: Dict):
        self.search = self.search.sort(keys)
        return self

    def agg(self, field_name: str, agg: Agg):
        self.search.aggs[field_name] = agg
        return self

    def highlight(self, *fields: str, highlight_query: Optional[Dict]):
        """request highlighting of some fields"""
        if not highlight_query:
            if self.search.query:
                highlight_query = self.search.query.to_dict()
            else:
                highlight_query = Q().to_dict()
        self.search = (
            self.search.highlight(*fields, number_of_fragments=0)
            .highlight_options(pre_tags=[pre_tag], post_tags=[post_tag], require_field_match=False)
            .highlight_options(highlight_query=highlight_query)
        )
        return self

    def to_dict(self, count: bool = False):
        """Serialize the search into the dictionary that will be sent over as the request's body."""
        return self.search.to_dict(count=count)
