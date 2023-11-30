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
from django.test import TestCase

from paasng.infras.accounts.oauth.constants import ScopeType
from paasng.infras.accounts.oauth.models import Scope


class TestScope(TestCase):
    def setUp(self):
        pass

    def test_match_different_scope(self):
        scope = Scope.parse_from_str("group:v3-test-group")
        assert scope.type == ScopeType.GROUP
        assert scope.item == "v3-test-group"

        scope = Scope.parse_from_str("project:admin/Skynet")
        assert scope.type == ScopeType.PROJECT
        assert scope.item == "admin/Skynet"

        scope = Scope.parse_from_str("project:admin_yu/Sky-net")
        assert scope.type == ScopeType.PROJECT
        assert scope.item == "admin_yu/Sky-net"

        scope = Scope.parse_from_str("user:user")
        assert scope.type == ScopeType.USER
        assert scope.item == "user"

        scope = Scope.parse_from_str("api")
        assert scope.type == ScopeType.USER
        assert scope.item == "user"

        scope = Scope.parse_from_str("")
        assert scope.type == ScopeType.USER
        assert scope.item == "user"

    def test_error_match(self):
        with pytest.raises(AttributeError):
            _ = Scope.parse_from_str("asdfasdf")

        with pytest.raises(ValueError, match=r".*is not a valid ScopeType"):
            _ = Scope.parse_from_str("a:b")
