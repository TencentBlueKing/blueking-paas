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

from contextlib import nullcontext

import pytest
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.test import override_settings
from django_dynamic_fixture import G

from paasng.platform.modules.constants import APP_CATEGORY, SourceOrigin
from paasng.platform.modules.models import AppSlugBuilder, AppSlugRunner, BuildConfig

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("model_class", [AppSlugBuilder, AppSlugRunner])
class TestAppImageModel:
    @pytest.mark.parametrize(
        ("region", "is_hidden", "expect_empty"),
        [
            (..., False, False),
            (..., True, True),
            ("random_name", True, True),
        ],
    )
    def test_filter(self, request, bk_module, model_class, region, is_hidden, expect_empty):
        if region is not ...:
            region = request.getfixturevalue(region)
        else:
            region = bk_module.region
        instance = G(model_class, region=region, is_hidden=is_hidden)
        expected = [] if expect_empty else [instance]
        assert list(model_class.objects.filter_module_available(bk_module)) == expected

    @pytest.mark.parametrize(
        ("image", "tag", "full_image", "expect_empty"),
        [
            ("aaaa", "latest", "aaaa:latest", False),
            ("bbbb", "latest", "aaaa:latest", True),
            ("aaaa", "bbbb", "aaaa:latest", True),
        ],
    )
    def test_filter_full_image(self, bk_module, model_class, image, tag, full_image, expect_empty):
        instance = G(model_class, region=bk_module.region, image=image, tag=tag)
        expected = [] if expect_empty else [instance]
        assert list(type(instance).objects.filter_by_full_image(bk_module, full_image)) == expected

    @pytest.mark.parametrize(
        ("labels", "language", "source_origin", "expect_matched", "expect_empty"),
        [
            ({"language": "Python", "category": "smart_app"}, "Python", SourceOrigin.S_MART.value, True, False),
            (
                {"language": "Python", "category": "smart_app"},
                "Python",
                SourceOrigin.AUTHORIZED_VCS.value,
                False,
                False,
            ),
            ({"language": "Python", "category": "smart_app"}, "NodeJS", SourceOrigin.S_MART.value, False, False),
            (
                {"language": "Python", "category": "smart_app"},
                "NodeJS",
                SourceOrigin.AUTHORIZED_VCS.value,
                False,
                False,
            ),
            ({}, "Python", SourceOrigin.AUTHORIZED_VCS.value, False, False),
        ],
    )
    def test_filter_by_labels(
        self, bk_module, model_class, labels, language, source_origin, expect_matched, expect_empty
    ):
        instance = G(model_class, region=bk_module.region)
        for key in labels:
            instance.set_label(key, labels[key])
        runtime_labels = {"language": language}
        if source_origin == SourceOrigin.S_MART.value:
            runtime_labels["category"] = APP_CATEGORY.S_MART_APP.value
        else:
            runtime_labels["category"] = APP_CATEGORY.NORMAL_APP.value
        available_qs = type(instance).objects.filter_by_labels(bk_module, runtime_labels)
        if expect_matched:
            assert available_qs.count() > 0
            assert list(available_qs) == [] if expect_empty else [instance]
        else:
            assert available_qs.count() == 0

    @pytest.mark.parametrize(
        ("runtimes", "labels", "ctx"),
        [
            # 测试 is_default
            ([{"name": "a", "is_default": True}], {}, nullcontext("a")),
            ([{"name": "a", "is_default": True}, {"name": "b"}], {}, nullcontext("a")),
            ([{"name": "a", "is_default": True}, {"name": "b", "is_default": True}], {}, nullcontext("b")),
            # 测试 select by labels
            ([{"name": "a", "labels": {"normal_app": "1"}}], {}, pytest.raises(ObjectDoesNotExist)),
            ([{"name": "a", "labels": {"normal_app": "1"}}], {"normal_app": "1"}, nullcontext("a")),
            (
                [{"name": "a", "labels": {"normal_app": "1"}}, {"name": "b", "labels": {"normal_app": "1"}}],
                {"normal_app": "1"},
                nullcontext("b"),
            ),
            (
                [
                    {"name": "a", "labels": {"normal_app": "1"}, "is_default": True},
                    {"name": "b", "labels": {"normal_app": "1"}},
                ],
                {"normal_app": "1"},
                nullcontext("a"),
            ),
            (
                [
                    {"name": "a", "labels": {"normal_app": "1"}, "is_default": True},
                    {"name": "b", "labels": {"normal_app": "1"}},
                    {"name": "c", "labels": {"normal_app": "1"}, "is_default": True},
                ],
                {"normal_app": "1"},
                nullcontext("c"),
            ),
            # 测试 select by settings
            ([{"name": "a"}, {"name": "foo"}], {}, nullcontext("foo")),
        ],
    )
    @override_settings(DEFAULT_RUNTIME_IMAGES={settings.DEFAULT_REGION_NAME: "foo"})
    def test_select_default_runtime(self, bk_module, model_class, runtimes, labels, ctx):
        for args in runtimes:
            G(model_class, region=settings.DEFAULT_REGION_NAME, **args)

        with ctx as expected_name:
            instance = model_class.objects.select_default_runtime(region=settings.DEFAULT_REGION_NAME, labels=labels)
            assert instance is not None
            assert instance.name == expected_name


class TestAppSlugBuilder:
    @pytest.mark.parametrize(
        ("region", "is_hidden", "bind", "expect_empty"),
        [
            ("random_name", False, False, True),
            ("random_name", True, False, True),
            ("random_name", True, True, False),
            ("random_name", False, True, False),
            (..., False, True, False),
            (..., True, True, False),
            (..., True, False, True),
            (..., False, False, False),
        ],
    )
    def test_get_buildpack_choices(
        self, request, bk_module, buildpack, slugbuilder, region, is_hidden, bind, expect_empty
    ):
        build_config = BuildConfig.objects.get_or_create_by_module(bk_module)
        if region is not ...:
            buildpack.region = request.getfixturevalue(region)
        if bind:
            build_config.buildpacks.add(buildpack)
        buildpack.is_hidden = is_hidden
        buildpack.save()

        expected = [] if expect_empty else [buildpack]
        assert slugbuilder.get_buildpack_choices(bk_module) == expected
