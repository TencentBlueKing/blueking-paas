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
import itertools
import logging
from dataclasses import dataclass, field
from datetime import datetime
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings

from .serializers import DocumentSLZ

logger = logging.getLogger(__name__)


@dataclass
class SearchDocumentary:
    """search documentary object"""

    source_type: str
    title: str
    url: str
    # digest field may include highlight info
    digest: Optional[str] = None

    author_name: Optional[str] = None
    updated_at: Optional[datetime] = None


@dataclass
class SearchDocResults:
    """Search results"""

    docs: List[SearchDocumentary]
    count: int
    extra: Dict[str, Any] = field(default_factory=dict)


def get_json_response(resp: requests.Response, only_allow_ok_status=True) -> Any:
    """Return response as JSON object if it's a valid JSON string

    :param only_allow_ok_status: Only status codes between 200 and 299 are considered valid
    :raises: ValueError when response is not valid
    """
    if not (200 <= resp.status_code <= 299):
        logger.warning("Got invalid status_code: %s from response", resp.status_code)
        raise ValueError('status_code invalid')

    try:
        return resp.json()
    except JSONDecodeError:
        logger.warning("Response is not valid JSON string, response: %s", repr(resp.text[:100]))
        raise ValueError('content is not valid JSON')


class BaseSearcher:
    def search(self, keyword: str) -> SearchDocResults:
        raise NotImplementedError


class BKDocumentSearcher(BaseSearcher):
    BKDOC_SEARCH_BASE_URL = settings.BKDOC_URL + '/search/?keyword={}'

    def search(self, keyword: str) -> SearchDocResults:
        """Call blueking document API to get matching documents"""
        resp = requests.get(self.BKDOC_SEARCH_BASE_URL.format(keyword))
        try:
            json_data = get_json_response(resp)
        except ValueError:
            return SearchDocResults(docs=[], count=0)

        results = []
        for item in json_data:
            url = settings.BKDOC_URL + item['url']
            results.append(
                SearchDocumentary(source_type='bk_document', title=item['title'], url=url, digest=item["digest"])
            )
        return SearchDocResults(docs=results, count=len(results))


SEARCHER_CLS = [BKDocumentSearcher]
try:
    from .backends_ext import update_searcher_cls

    SEARCHER_CLS = update_searcher_cls(SEARCHER_CLS)
except ImportError:
    pass


class MixSearcher:
    def __init__(self):
        self.searchers = [cls() for cls in SEARCHER_CLS]

    @staticmethod
    def to_simple_payload(doc: SearchDocumentary) -> Dict:
        """Turn SearchDocumentary object into simple json payload"""
        return DocumentSLZ(doc).data

    def search(self, keyword: str) -> List[Dict]:
        search_results = [searcher.search(keyword).docs for searcher in self.searchers]
        items = []
        for item in itertools.zip_longest(*search_results):
            # 按 1:1 混合各个 searcher 的结果
            items.extend([i for i in item if i is not None])
        return [self.to_simple_payload(doc) for doc in items]
