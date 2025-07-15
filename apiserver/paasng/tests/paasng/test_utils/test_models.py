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

import pickle

import pytest
from attrs import define
from bkpaas_auth.core.constants import ProviderType
from bkpaas_auth.core.encoder import user_id_encoder
from blue_krill.contextlib import nullcontext as does_not_raise
from django.db import models
from django_dynamic_fixture import G

from paasng.infras.accounts.models import UserProfile
from paasng.platform.applications.constants import ApplicationType
from paasng.platform.applications.utils import create_application
from paasng.utils.models import BkUserField, OrderByField, make_json_field, make_legacy_json_field
from tests.utils.basic import generate_random_string

pytestmark = pytest.mark.django_db


class TestUtils:
    def test_bk_user_field(self):
        profile = G(UserProfile, user="0235cce79c92")
        profile = UserProfile.objects.get(pk=profile.pk)

        assert profile.user == "0235cce79c92"
        assert profile.user.username == "admin"


class TestOrderByField:
    def test_from_string(self):
        f = OrderByField.from_string("-created")
        assert f.is_descending is True
        assert f.name == "created"

        f = OrderByField.from_string("created")
        assert f.is_descending is False
        assert f.name == "created"

    def test_replacing_name(self):
        f = OrderByField.from_string("-created")
        f.name = "updated"
        assert str(f) == "-updated"


def test_make_legacy_json_field():
    @define
    class Dummy:
        a: str

    DummyField = make_legacy_json_field("DummyField", Dummy)  # noqa: N806
    assert DummyField.__module__ == __name__
    assert DummyField.__name__ == "DummyField"


def test_make_json_field():
    @define
    class Dummy:
        a: str

    DummyField = make_json_field("DummyField", Dummy)  # noqa: N806
    assert DummyField.__module__ == __name__
    assert DummyField.__name__ == "DummyField"


@define
class Baz:
    pickle: bool


# 注: 这里的左值变量名必须和右值函数参数的 cls_name 一致.
PickleAbleField1 = make_legacy_json_field("PickleAbleField1", Baz)
PickleAbleField2 = make_json_field("PickleAbleField2", Baz)
# 注: 这里的左值变量名必须和右值函数参数的 cls_name 不一致.
UnPickleAbleField = make_legacy_json_field("NotAPickleAbleField", Baz)


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        (PickleAbleField1, does_not_raise()),
        (PickleAbleField2, does_not_raise()),
        (UnPickleAbleField, pytest.raises(pickle.PicklingError)),
    ],
)
def test_pickle(field, expected):
    with expected:
        pickle.dumps(field)


class TestBkUserField:
    def test_set(self):
        class M(models.Model):
            creator = BkUserField()

            class Meta:
                app_label = "foo"

        foo_u = user_id_encoder.encode(ProviderType.BK, "foo")
        instance = M(creator=foo_u)
        assert instance.creator.username == "foo"

        bar_u = user_id_encoder.encode(ProviderType.BK, "bar")
        instance.creator = bar_u
        assert instance.creator.username == "bar"

        instance.creator = None  # type: ignore
        assert instance.creator is None

        baz_u = user_id_encoder.encode(ProviderType.BK, "baz")
        instance.creator = baz_u
        assert instance.creator.username == "baz"

    def test_integrated(self):
        application = create_application(
            code=generate_random_string(6),
            name=generate_random_string(6),
            name_en=generate_random_string(6),
            app_type=ApplicationType.DEFAULT,
            operator=user_id_encoder.encode(ProviderType.BK, "foo"),
            is_plugin_app=False,
        )
        assert application.creator.username == "foo"

        application.creator = user_id_encoder.encode(ProviderType.BK, "bar")
        application.save()
        assert application.creator.username == "bar"
