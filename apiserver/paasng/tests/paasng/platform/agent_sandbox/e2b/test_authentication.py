# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory

from paasng.platform.agent_sandbox.e2b.authentication import E2BApiKeyAuthentication, E2BPrincipal
from paasng.platform.agent_sandbox.e2b.base_views import E2BProtocolViewSet
from paasng.platform.agent_sandbox.e2b.permissions import IsE2BApiKey
from paasng.platform.agent_sandbox.models import E2BApiKey

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

# 格式合法但从未签发过的 key。这里必须是固定字面量而不是 generate_api_key()：
# 参数化在收集阶段求值，随机值会让 xdist 各 worker 收集到不同的用例 ID 而报错
UNKNOWN_KEY = "e2b_" + "0" * 39 + "1"


@pytest.fixture()
def issued_key(bk_app, bk_user):
    return E2BApiKey.objects.issue(application=bk_app, owner=bk_user.pk)


def _authenticate(raw_key=None):
    headers = {"HTTP_X_API_KEY": raw_key} if raw_key is not None else {}
    request = APIRequestFactory().get("/e2b/sandboxes", **headers)
    return E2BApiKeyAuthentication().authenticate(request)


class TestAuthenticate:
    def test_valid_key_resolves_subject(self, bk_app, issued_key):
        """认证通过后能取到正确的归属主体。"""
        key_obj, plain_key = issued_key

        principal, auth = _authenticate(plain_key)

        assert principal.is_authenticated is True
        assert principal.application == bk_app
        assert principal.tenant_id == bk_app.tenant_id
        assert auth.pk == key_obj.pk

    @pytest.mark.parametrize(
        "raw_key",
        [
            # 不带凭证
            None,
            "",
            # 格式非法，SDK 侧也会拒绝
            "not-an-e2b-key",
            "e2b_ZZZZ",
            # 格式合法但库里没有
            UNKNOWN_KEY,
        ],
    )
    def test_rejects_invalid_key(self, raw_key):
        with pytest.raises(AuthenticationFailed):
            _authenticate(raw_key)

    def test_revoked_key_is_rejected_identically(self, issued_key):
        """已吊销与不存在返回完全一致的错误，不泄露差异。"""
        key_obj, plain_key = issued_key
        key_obj.revoke()

        with pytest.raises(AuthenticationFailed) as revoked:
            _authenticate(plain_key)
        with pytest.raises(AuthenticationFailed) as unknown:
            _authenticate(UNKNOWN_KEY)

        assert str(revoked.value) == str(unknown.value)
        assert revoked.value.status_code == unknown.value.status_code

    def test_malformed_key_does_not_hit_db(self, django_assert_num_queries):
        """格式非法的 key 在查库之前就被挡掉。"""
        with django_assert_num_queries(0), pytest.raises(AuthenticationFailed):
            _authenticate("bad-key")

    def test_valid_key_costs_one_query(self, issued_key, django_assert_num_queries):
        """认证走在每个 e2b 请求上，路径上只允许一次查询且不做任何写入。"""
        _, plain_key = issued_key

        with django_assert_num_queries(1):
            _authenticate(plain_key)


class _ProbeViewSet(E2BProtocolViewSet):
    """只用于验证认证与错误响应形态的探针视图。"""

    def probe(self, request):
        return Response({"app": self.application.code, "prefix": self.api_key.key_prefix})


class TestProtocolViewSet:
    def test_unauthenticated_response_matches_e2b_shape(self):
        """e2b SDK 只认 message 字段，且响应里不能出现平台的登录地址。"""
        request = APIRequestFactory().get("/e2b/probe")
        resp = _ProbeViewSet.as_view({"get": "probe"})(request)
        resp.render()

        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
        body = resp.data
        assert set(body) == {"code", "message"}
        assert body["code"] == status.HTTP_401_UNAUTHORIZED
        assert "login_url" not in resp.content.decode()

    def test_authenticated_request_reaches_view(self, bk_app, issued_key):
        key_obj, plain_key = issued_key
        request = APIRequestFactory().get("/e2b/probe", HTTP_X_API_KEY=plain_key)

        resp = _ProbeViewSet.as_view({"get": "probe"})(request)

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data == {"app": bk_app.code, "prefix": key_obj.key_prefix}


class TestIsE2BApiKey:
    def test_accepts_e2b_principal(self, issued_key):
        key_obj, _ = issued_key
        request = APIRequestFactory().get("/e2b/probe")
        request.user = E2BPrincipal(api_key=key_obj)

        assert IsE2BApiKey().has_permission(request, view=None) is True

    def test_rejects_platform_user(self, bk_user):
        """平台登录态不能冒充 Key 主体访问协议端点。"""
        request = APIRequestFactory().get("/e2b/probe")
        request.user = bk_user

        assert IsE2BApiKey().has_permission(request, view=None) is False
