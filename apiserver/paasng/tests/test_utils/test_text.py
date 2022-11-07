# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import pytest

from paasng.utils.text import camel_to_snake, remove_suffix, strip_html_tags


class TestStripHTMLTags:
    @pytest.mark.parametrize(
        "s,reserved_tags,result",
        [
            ('foo', [], 'foo'),
            ('foo<bold></bold>bar', [], 'foobar'),
            ('foo<hl>bar</hl>', ['<hl>', '</hl>'], 'foo<hl>bar</hl>'),
            ('<blue>foo</blue><hl>bar</hl>', ['<hl>', '</hl>'], 'foo<hl>bar</hl>'),
        ],
    )
    def test_normal(self, s, reserved_tags, result):
        assert strip_html_tags(s, reserved_tags=reserved_tags) == result


@pytest.mark.parametrize(
    'input_,suffix,output',
    [
        ('foo', 'bar', 'foo'),
        ('foobar', 'bar', 'foo'),
        ('foobar', 'foobar', ''),
    ],
)
def test_remove_suffix(input_, suffix, output):
    assert remove_suffix(input_, suffix) == output


@pytest.mark.parametrize(
    'input_,output',
    [
        ('BkSvnSourceTypeSpec', 'bk_svn_source_type_spec'),
        ('bk_svn', 'bk_svn'),
    ],
)
def test_camel_to_snake(input_, output):
    assert camel_to_snake(input_) == output
