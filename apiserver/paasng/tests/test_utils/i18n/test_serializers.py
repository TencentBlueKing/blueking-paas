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
from contextlib import nullcontext

import pytest
from django.test.utils import override_settings
from django.utils.translation import override
from rest_framework import serializers

from paasng.utils.i18n.serializers import I18NExtend, TranslatedCharField, i18n


@pytest.fixture(autouse=True)
def setup_languages():
    with override_settings(LANGUAGES=[("en", "English"), ("zh-cn", "简体中文")]):
        yield


@pytest.fixture
def serializer_class():
    class DummySLZ(serializers.Serializer):
        A = serializers.CharField(required=False, allow_blank=True, default='')
        B = TranslatedCharField(required=False, allow_blank=True, default='')
        C = I18NExtend(serializers.CharField(required=False, allow_blank=True, default=''))

    return DummySLZ


@pytest.fixture
def i18n_serializer_class(serializer_class):
    @i18n
    class DummySLZ(serializers.Serializer):
        A = serializers.CharField(required=False, allow_blank=True, default='')
        C = I18NExtend(serializers.CharField(required=False, allow_blank=True, default=''))

    return DummySLZ


class TestTranslatedCharField:
    @pytest.mark.parametrize(
        "init_kwargs, ctx, expected",
        [
            ({}, nullcontext(), {"A": "", "B": ""}),
            ({"B": "beta"}, nullcontext(), {"A": "", "B": "beta"}),
            ({"b_en": "beta", "b_zh_cn": "贝塔"}, override("en"), {"A": "", "B": "beta"}),
            ({"b_en": "beta", "b_zh_cn": "贝塔"}, override("zh-cn"), {"A": "", "B": "贝塔"}),
        ],
    )
    def test_validate(self, serializer_class, init_kwargs, ctx, expected):
        slz = serializer_class(data=init_kwargs)
        slz.is_valid(raise_exception=True)
        with ctx:
            assert slz.validated_data == expected

    @pytest.mark.parametrize(
        "init_kwargs, ctx, expected",
        [
            ({}, nullcontext(), {"A": "", "B": ""}),
            ({"B": "beta"}, nullcontext(), {"A": "", "B": "beta"}),
            ({"b_en": "beta", "b_zh_cn": "贝塔"}, override("en"), {"A": "", "B": "beta"}),
            ({"b_en": "beta", "b_zh_cn": "贝塔"}, override("zh-cn"), {"A": "", "B": "贝塔"}),
        ],
    )
    def test_to_representation(self, serializer_class, init_kwargs, ctx, expected):
        slz = serializer_class(instance=init_kwargs)
        with ctx:
            assert slz.data == expected


class TestTranslatedField:
    @pytest.mark.parametrize(
        "init_kwargs, ctx, expected",
        [
            ({}, nullcontext(), {"A": "", "c_en": '', "c_zh_cn": ""}),
            ({"C": "delta"}, nullcontext(), {"A": "", "c_en": 'delta', "c_zh_cn": "delta"}),
            ({"c_en": "delta", "c_zh_cn": "德尔塔"}, override("en"), {"A": "", "c_en": 'delta', "c_zh_cn": "德尔塔"}),
            ({"c_en": "delta", "c_zh_cn": "德尔塔"}, override("zh-cn"), {"A": "", "c_en": 'delta', "c_zh_cn": "德尔塔"}),
        ],
    )
    def test_validate(self, i18n_serializer_class, init_kwargs, ctx, expected):
        slz = i18n_serializer_class(data=init_kwargs)
        slz.is_valid(raise_exception=True)
        with ctx:
            assert slz.validated_data == expected
