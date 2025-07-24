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

import pytest

from paas_wl.workloads.networking.entrance.serializers import DomainEditableMixin

pytestmark = pytest.mark.django_db(databases=["workloads"])


class TestDomainEditableMixin:
    @pytest.mark.parametrize(
        ("path_prefix", "want_is_valid", "want_path_prefix"),
        [
            (None, True, "/"),
            ("", True, "/"),
            ("/foo/", True, "/foo/"),
            ("/foo/bar/", True, "/foo/bar/"),
            # Does not match pattern
            ("/foo///", False, None),
            ("foobar", False, None),
        ],
    )
    def test_path_prefix(self, path_prefix, want_is_valid, want_path_prefix):
        data = {"path_prefix": path_prefix, "domain_name": "example.com"}
        slz = DomainEditableMixin(data=data)
        is_valid = slz.is_valid()

        assert is_valid is want_is_valid
        if is_valid:
            assert slz.validated_data["path_prefix"] == want_path_prefix
