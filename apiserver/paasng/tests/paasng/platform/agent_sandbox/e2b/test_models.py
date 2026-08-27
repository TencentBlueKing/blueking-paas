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

from unittest import mock

import pytest

from paasng.platform.agent_sandbox.e2b.constants import MAX_ACTIVE_KEYS_PER_APP
from paasng.platform.agent_sandbox.e2b.exceptions import E2BApiKeyGenerateError, E2BApiKeyQuotaExceeded
from paasng.platform.agent_sandbox.e2b.keys import hash_api_key
from paasng.platform.agent_sandbox.models import E2BApiKey

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestIssue:
    def test_plaintext_is_not_persisted(self, bk_app, bk_user):
        """库里只有摘要和前缀，没有明文。"""
        key_obj, plain_key = E2BApiKey.objects.issue(application=bk_app, owner=bk_user.pk, name="ci")

        assert key_obj.key_hash == hash_api_key(plain_key)
        assert key_obj.key_prefix == plain_key[:12]
        assert plain_key not in (key_obj.key_hash, key_obj.key_prefix)

        # 整行序列化后也不应出现明文
        row = E2BApiKey.objects.filter(pk=key_obj.pk).values().first()
        assert plain_key not in str(row)

    def test_inherits_application_attribution(self, bk_app, bk_user):
        key_obj, _ = E2BApiKey.objects.issue(application=bk_app, owner=bk_user.pk)

        assert key_obj.application == bk_app
        assert key_obj.tenant_id == bk_app.tenant_id
        assert key_obj.owner == bk_user.pk
        assert key_obj.enabled is True
        assert key_obj.revoked_at is None

    def test_quota_counts_only_active_keys(self, bk_app, bk_user):
        """达到上限后拒绝签发，吊销一枚即可腾出名额。"""
        keys = [
            E2BApiKey.objects.issue(application=bk_app, owner=bk_user.pk)[0] for _ in range(MAX_ACTIVE_KEYS_PER_APP)
        ]

        with pytest.raises(E2BApiKeyQuotaExceeded):
            E2BApiKey.objects.issue(application=bk_app, owner=bk_user.pk)

        keys[0].revoke()
        assert E2BApiKey.objects.issue(application=bk_app, owner=bk_user.pk)[0].enabled is True

    def test_quota_is_per_application(self, bk_app, bk_user, bk_app_full):
        for _ in range(MAX_ACTIVE_KEYS_PER_APP):
            E2BApiKey.objects.issue(application=bk_app, owner=bk_user.pk)

        # 另一个应用的名额不受影响
        other_key, _ = E2BApiKey.objects.issue(application=bk_app_full, owner=bk_user.pk)
        assert other_key.application == bk_app_full

    def test_raises_when_generated_key_keeps_colliding(self, bk_app, bk_user):
        """撞上已有记录时应当报错，而不是覆盖别人的 key。"""
        _, existing_plain_key = E2BApiKey.objects.issue(application=bk_app, owner=bk_user.pk)

        # 让生成器每次都吐出一个已存在的 key，制造真实碰撞而不是 mock 掉查询
        with (
            mock.patch(
                "paasng.platform.agent_sandbox.models.generate_api_key",
                return_value=existing_plain_key,
            ),
            pytest.raises(E2BApiKeyGenerateError),
        ):
            E2BApiKey.objects.issue(application=bk_app, owner=bk_user.pk)

    def test_hash_length_matches_model_field(self, bk_app, bk_user):
        """摘要长度必须与 key_hash 的 max_length 一致，换哈希算法时不能悄悄截断。"""
        key_obj, _ = E2BApiKey.objects.issue(application=bk_app, owner=bk_user.pk)

        assert len(key_obj.key_hash) == E2BApiKey._meta.get_field("key_hash").max_length


class TestRevoke:
    def test_revoke_disables_without_deleting(self, bk_app, bk_user):
        """吊销是置为失效而非物理删除，审计线索要留着；重复吊销不改写时间。"""
        key_obj, _ = E2BApiKey.objects.issue(application=bk_app, owner=bk_user.pk)

        key_obj.revoke()
        first_revoked_at = key_obj.revoked_at
        assert key_obj.enabled is False
        assert first_revoked_at is not None
        assert E2BApiKey.objects.filter(pk=key_obj.pk).exists()

        key_obj.revoke()
        assert key_obj.revoked_at == first_revoked_at
