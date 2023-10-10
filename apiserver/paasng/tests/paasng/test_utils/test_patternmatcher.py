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

from paasng.utils.patternmatcher import Pattern


@pytest.mark.parametrize(
    "pattern, path, expected",
    [
        ("**", "file", True),
        ("**", "file/", True),
        ("**/", "file", False),
        ("**/", "file/", True),
        ("**", "/", True),
        ("**/", "/", True),
        ("**", "dir/file", True),
        ("**/", "dir/file", False),
        ("**", "dir/file/", True),
        ("**/", "dir/file/", True),
        ("**/**", "dir/file", True),
        ("**/**", "dir/file/", True),
        ("dir/**", "dir/file", True),
        ("dir/**", "dir/file/", True),
        ("dir/**", "dir/dir2/file", True),
        ("dir/**", "dir/dir2/file/", True),
        ("**/dir2/*", "dir/dir2/file", True),
        ("**/dir2/*", "dir/dir2/file/", False),
        ("**/dir2/**", "dir/dir2/dir3/file", True),
        ("**/dir2/**", "dir/dir2/dir3/file/", True),
        ("**file", "file", True),
        ("**file", "dir/file", True),
        ("**/file", "dir/file", True),
        ("**file", "dir/dir/file", True),
        ("**/file", "dir/dir/file", True),
        ("**/file*", "dir/dir/file", True),
        ("**/file*", "dir/dir/file.txt", True),
        ("**/file*txt", "dir/dir/file.txt", True),
        ("**/file*.txt", "dir/dir/file.txt", True),
        ("**/file*.txt*", "dir/dir/file.txt", True),
        ("**/**/*.txt", "dir/dir/file.txt", True),
        ("**/**/*.txt2", "dir/dir/file.txt", False),
        ("**/*.txt", "file.txt", True),
        ("**/**/*.txt", "file.txt", True),
        ("a**/*.txt", "a/file.txt", True),
        ("a**/*.txt", "a/dir/file.txt", True),
        ("a**/*.txt", "a/dir/dir/file.txt", True),
        ("a/*.txt", "a/dir/file.txt", False),
        ("a/*.txt", "a/file.txt", True),
        ("a/*.txt**", "a/file.txt", True),
        ("a[b-d]e", "ae", False),
        ("a[b-d]e", "ace", True),
        ("a[b-d]e", "aae", False),
        ("a[^b-d]e", "aze", True),
        (".*", ".foo", True),
        (".*", "foo", False),
        ("abc.def", "abcdef", False),
        ("abc.def", "abc.def", True),
        ("abc.def", "abcZdef", False),
        ("abc?def", "abcZdef", True),
        ("abc?def", "abcdef", False),
        ("a\\*b", "a*b", True),
        ("a\\", "a", False),
        ("a\\", "a\\", True),
        ("a\\\\", "a\\", True),
        ("**/foo/bar", "foo/bar", True),
        ("**/foo/bar", "dir/foo/bar", True),
        ("**/foo/bar", "dir/dir2/foo/bar", True),
        ("abc/**", "abc", False),
        ("abc/**", "abc/def", True),
        ("abc/**", "abc/def/ghi", True),
    ],
)
def test_pattern(pattern, path, expected):
    assert Pattern(pattern).match(path) is expected
