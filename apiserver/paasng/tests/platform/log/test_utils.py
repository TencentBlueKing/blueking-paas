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
from typing import Dict, List

import pytest

from paasng.platform.log.utils import get_es_term


class TestUtils:
    @pytest.fixture
    def make_stats_indexes_fake_resp(self):
        def _make_stats_indexes_fake_resp(indexes: List[str]):
            def _wrapper(*args, **kwargs):
                results: Dict[str, Dict] = {}
                for index in indexes:
                    results[index] = {}

                return {"indices": results}

            return _wrapper

        return _make_stats_indexes_fake_resp

    @pytest.mark.parametrize(
        "query_term,mappings,expected",
        [
            ("dd", {"dd": {"type": "text"}}, "dd.keyword"),
            ("dd", {"dd": {"type": "int"}}, "dd"),
            ("dd", {"dd": {"type": "keyword"}}, "dd"),
            ("dd", {"xxx": {"type": "keyword"}}, "dd"),
            ("json.levelname", {"json": {"properties": {"levelname": {"type": "text"}}}}, "json.levelname.keyword"),
            ("json.levelname", {"json": {"properties": {"levelname": {"type": "keyword"}}}}, "json.levelname"),
            (
                "json.levelname.no",
                {"json": {"properties": {"levelname": {"properties": {"no": {"type": "keyword"}}}}}},
                "json.levelname.no",
            ),
            (
                "json.levelname.no",
                {"json": {"properties": {"levelname": {"properties": {"no": {"type": "text"}}}}}},
                "json.levelname.no.keyword",
            ),
        ],
    )
    def test_get_es_term(self, query_term, mappings, expected):
        assert get_es_term(query_term, mappings) == expected
