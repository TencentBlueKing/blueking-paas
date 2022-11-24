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
import pytest

from paasng.platform.modules.constants import APP_CATEGORY, SourceOrigin
from paasng.platform.modules.models import AppSlugBuilder, AppSlugRunner
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db


class TestAppSlugBuilder:
    @pytest.mark.parametrize(
        "region, is_hidden, expect_empty",
        [
            (..., False, False),
            (..., True, True),
            (generate_random_string(), True, True),
            (generate_random_string(), True, True),
        ],
    )
    def test_filter(self, bk_module, slugbuilder, region, is_hidden, expect_empty):
        if region is not ...:
            slugbuilder.region = region
        slugbuilder.is_hidden = is_hidden
        slugbuilder.save()

        expected = [] if expect_empty else [slugbuilder]
        assert list(AppSlugBuilder.objects.filter_available(bk_module)) == expected

    @pytest.mark.parametrize(
        "image, tag, full_image, expect_empty",
        [
            ("aaaa", "latest", "aaaa:latest", False),
            ("bbbb", "latest", "aaaa:latest", True),
        ],
    )
    def test_filter_full_image(self, bk_module, slugbuilder, image, tag, full_image, expect_empty):
        slugbuilder.image = image
        slugbuilder.tag = tag
        slugbuilder.save()

        expected = [] if expect_empty else [slugbuilder]
        assert list(AppSlugBuilder.objects.filter_by_full_image(bk_module, full_image)) == expected

    @pytest.mark.parametrize(
        "region, is_hidden, bind, expect_empty",
        [
            (generate_random_string(), False, False, True),
            (generate_random_string(), True, False, True),
            (generate_random_string(), True, True, False),
            (generate_random_string(), False, True, False),
            (..., False, True, False),
            (..., True, True, False),
            (..., True, False, True),
            (..., False, False, False),
        ],
    )
    def test_get_buildpack_choices(self, bk_module, buildpack, slugbuilder, region, is_hidden, bind, expect_empty):
        if region is not ...:
            buildpack.region = region
        if bind:
            buildpack.modules.add(bk_module)
        buildpack.is_hidden = is_hidden
        buildpack.save()

        expected = [] if expect_empty else [buildpack]
        assert slugbuilder.get_buildpack_choices(bk_module) == expected

    @pytest.mark.parametrize(
        "labels, language, source_origin, expect_matched, expect_empty",
        [
            # ({"language": "Python", "category": "smart_app"}, "Python", SourceOrigin.S_MART.value, True, False),
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
    def test_filter_by_label(
        self, bk_module, slugbuilder, labels, language, source_origin, expect_matched, expect_empty
    ):
        for key in labels:
            slugbuilder.set_label(key, labels[key])
        slugbuilder.region = bk_module.region
        slugbuilder.save()

        runtime_labels = {"language": language}
        if source_origin == SourceOrigin.S_MART.value:
            runtime_labels["category"] = APP_CATEGORY.S_MART_APP.value
        else:
            runtime_labels["category"] = APP_CATEGORY.NORMAL_APP.value
        matched, availables = AppSlugBuilder.objects.filter_by_label(bk_module, runtime_labels)

        assert matched == expect_matched
        assert list(availables) == [] if expect_empty else [slugbuilder]


class TestAppSlugRunner:
    @pytest.mark.parametrize(
        "region, is_hidden, expect_empty",
        [
            (..., False, False),
            (..., True, True),
            (generate_random_string(), True, True),
            (generate_random_string(), True, True),
        ],
    )
    def test_filter(self, bk_module, slugrunner, region, is_hidden, expect_empty):
        if region is not ...:
            slugrunner.region = region
        slugrunner.is_hidden = is_hidden
        slugrunner.save()

        expected = [] if expect_empty else [slugrunner]
        assert list(AppSlugRunner.objects.filter_available(bk_module)) == expected
