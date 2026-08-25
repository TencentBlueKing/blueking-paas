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
from bkpaas_auth.core.constants import ProviderType
from bkpaas_auth.core.encoder import user_id_encoder
from django.db import models

from app_spark_api.infras.accounts.models import UserProfile
from app_spark_api.utils.models import BkUserField, SimpleUserIDWrapper

pytestmark = pytest.mark.django_db


class TestUtils:
    def test_bk_user_field(self):
        profile = UserProfile.objects.create(user="0235cce79c92")
        profile = UserProfile.objects.get(pk=profile.pk)

        assert profile.user == "0235cce79c92"
        assert isinstance(profile.user, SimpleUserIDWrapper)
        assert profile.user.username == "admin"


class TestBkUserField:
    def test_set(self):
        class M(models.Model):
            creator = BkUserField()

            class Meta:
                app_label = "foo"

        foo_u = user_id_encoder.encode(ProviderType.BK, "foo")
        instance = M(creator=foo_u)
        assert isinstance(instance.creator, SimpleUserIDWrapper)
        assert instance.creator.username == "foo"

        bar_u = user_id_encoder.encode(ProviderType.BK, "bar")
        instance.creator = bar_u
        assert isinstance(instance.creator, SimpleUserIDWrapper)
        assert instance.creator.username == "bar"

        instance.creator = None
        assert instance.creator is None

        instance.creator = ""
        assert isinstance(instance.creator, SimpleUserIDWrapper)
        assert instance.creator == ""

        baz_u = user_id_encoder.encode(ProviderType.BK, "baz")
        instance.creator = baz_u
        assert isinstance(instance.creator, SimpleUserIDWrapper)
        assert instance.creator.username == "baz"
