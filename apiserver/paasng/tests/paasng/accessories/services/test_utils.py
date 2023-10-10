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
import logging
from dataclasses import dataclass

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.db import connections
from django.test import TestCase

from paasng.accessories.services.utils import Base36Handler, WRItemList, gen_unique_id, get_vendor_config

logger = logging.getLogger(__name__)


def test_get_vendor_config(settings):
    settings.SERVICES_VENDOR_CONFIGS = {'foo': {'timeout': 3}}

    @dataclass
    class ConfigCls:
        timeout: int

    assert get_vendor_config('foo', result_cls=ConfigCls).timeout == 3


def test_get_vendor_config_not_configured(settings):
    settings.SERVICES_VENDOR_CONFIGS = {}
    with pytest.raises(ImproperlyConfigured):
        assert get_vendor_config('foo', result_cls=type)


class TestWRR(TestCase):
    def test_normal(self):
        wr_list = WRItemList.from_json([{"values": "foo", "weight": 1}])
        assert wr_list.get().values == "foo"

    def test_no_weight(self):
        with pytest.raises(ValueError):
            WRItemList.from_json([{"values": "foo", "weight": 0}])

    def test_weight_zero(self):
        wr_list = WRItemList.from_json([{"values": "foo", "weight": 0}, {"values": "bar", "weight": 1}])
        results = []
        for _ in range(1000):
            results.append(wr_list.get().values)

        assert all(r == "bar" for r in results)

    def test_multi_weighted(self):
        wr_list = WRItemList.from_json(
            [
                {"values": "foo", "weight": 1},
                {"values": "bar", "weight": 9},
                {"values": "xyz", "weight": 0},
            ]
        )
        results = []
        for _ in range(1000):
            results.append(wr_list.get().values)

        # Below assertions is not 100% true because everything is based on random algorithm
        # even if it's "weighted"
        assert sum([r == "foo" for r in results]) > 50
        assert sum([r == "bar" for r in results]) > 450


class TestGetUniqueID(TestCase):
    @classmethod
    def setUpTestData(cls):
        with connections['default'].cursor() as cursor:
            # make a big id
            cursor.execute('ALTER table services_resourceid AUTO_INCREMENT=1000')

    def setUp(self) -> None:
        with connections['default'].cursor() as cursor:
            cursor.execute("INSERT INTO services_resourceid (namespace, uid) VALUES ('default', 'foo')")
            cursor.execute("SELECT LAST_INSERT_ID()")
            self.latest_id = cursor.fetchone()[0] + 1

    def test_normal(self):
        uid = "some-app"

        assert gen_unique_id(uid) == f"some-app-{Base36Handler.encode(self.latest_id)}"

    def test_max_length(self):
        # len(uid) is 14
        uid = "some-some-some"
        # Base62Handler.encode(1000) is 'rs', so reserve length of uid is 16 - 3 = 13
        assert gen_unique_id(uid) == f"some-some-som-{Base36Handler.encode(self.latest_id)}"
        # 14 + len("-rs") is 17
        assert gen_unique_id(uid, max_length=20) == f"some-some-some-{Base36Handler.encode(self.latest_id+1)}"

        # the length of six "some" is 24
        uid = "somesomesomesomesomesome"
        assert len(gen_unique_id(uid)) == 16
        assert len(gen_unique_id(uid, max_length=20)) == 20

    def test_divide_char(self):
        uid = "some-some-some"
        assert gen_unique_id(uid, divide_char="/") == f"some-some-som/{Base36Handler.encode(self.latest_id)}"

    def test_divide_char_max_length(self):
        # length: 19
        uid = "some-some-some-some"

        # len("////") + len('rs') is 6, so reserve length of original uid is 10
        assert gen_unique_id(uid, divide_char="////") == f"some-some-////{Base36Handler.encode(self.latest_id)}"
