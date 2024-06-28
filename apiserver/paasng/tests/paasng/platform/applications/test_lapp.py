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
from django.conf import settings

from paasng.core.core.storages.sqlalchemy import legacy_db
from tests.conftest import check_legacy_enabled
from tests.utils.helpers import adaptive_lapplicationtag_fields, generate_random_string

try:
    from paasng.infras.legacydb_te.adaptors import AppAdaptor, legacy_models
except ImportError:
    from paasng.infras.legacydb.adaptors import AppAdaptor, legacy_models  # type: ignore

pytestmark = pytest.mark.django_db


@pytest.fixture()
def legacy_app():
    if not check_legacy_enabled():
        raise pytest.skip("Legacy db engine is not initialized")
    code = generate_random_string(length=15)
    name = generate_random_string(length=15)

    with legacy_db.session_scope() as session:
        return AppAdaptor(session).create(code=code, name=name, deploy_ver=settings.DEFAULT_REGION_NAME)


@pytest.fixture()
def legacy_tag():
    if not check_legacy_enabled():
        raise pytest.skip("Legacy db engine is not initialized")

    code = generate_random_string(length=15)
    name = generate_random_string(length=15)

    field_values = dict(
        name=name,
        code=code,
        index=0,
        is_select=1,
    )
    tag = legacy_models.LApplicationTag(**adaptive_lapplicationtag_fields(field_values))
    with legacy_db.session_scope() as session:
        session.add(tag)
        session.commit()
    return tag


class TestLightAppViewSet:
    @pytest.mark.parametrize(
        ("data", "expected_info"),
        [
            (
                {
                    "app_name": "foo",
                    "app_url": "http://example.com",
                    "developers": ["admin"],
                    "app_tag": "Other",
                    "creator": "blueking",
                },
                {
                    "app_name": "foo",
                    "app_url": "http://example.com",
                    "introduction": "-",
                    "creator": "blueking",
                    "developers": ["admin"],
                    "state": 4,
                },
            ),
            (
                {
                    "app_name": "foo",
                    "app_url": "http://example.com",
                    "developers": ["admin"],
                    "app_tag": "Other",
                    "creator": "blueking",
                    "logo": "MQ==",
                    "introduction": "introduction",
                },
                {
                    "app_name": "foo",
                    "app_url": "http://example.com",
                    "introduction": "introduction",
                    "creator": "blueking",
                    "developers": ["admin"],
                    "state": 4,
                },
            ),
        ],
    )
    def test_create(self, legacy_tag, legacy_app, sys_light_api_client, data, expected_info):
        response = sys_light_api_client.post(
            "/sys/api/light-applications/",
            data={
                "parent_app_code": legacy_app.code,
                "app_tag": legacy_tag.code,
                **data,
            },
        )
        assert response.status_code == 200

        result = response.json()
        app_info = result.pop("data")
        logo = app_info.pop("logo")
        light_app_code = app_info.pop("light_app_code")

        assert light_app_code[:13] == legacy_app.code[:13]
        assert app_info == expected_info
        if "logo" in data:
            assert f"o_{light_app_code}.png" in logo

        assert result["bk_error_code"] == "0"
        assert result["bk_error_msg"] == ""
        assert result["result"]

    @pytest.mark.parametrize(
        ("is_lapp", "expected"),
        [
            (False, {"bk_error_msg": "{code} not found", "bk_error_code": "1301100", "data": None, "result": False}),
            (True, {"bk_error_msg": "", "bk_error_code": "0", "data": {"count": 1}, "result": True}),
        ],
    )
    def test_delete(self, legacy_app, sys_light_api_client, is_lapp, expected):
        with legacy_db.session_scope() as session:
            AppAdaptor(session).update(code=legacy_app.code, data={"is_lapp": is_lapp})

        response = sys_light_api_client.delete(
            "/sys/api/light-applications/?light_app_code=" + legacy_app.code,
        )
        assert response.status_code == 200
        result = response.json()

        assert result.pop("bk_error_msg") == expected.pop("bk_error_msg").format(code=legacy_app.code)
        assert result == expected

    @pytest.mark.parametrize(
        ("is_lapp", "expected"),
        [
            (False, {"bk_error_msg": "{code} not found", "bk_error_code": "1301100", "result": False}),
            (True, {"bk_error_msg": "", "bk_error_code": "0", "result": True}),
        ],
    )
    def test_query(self, legacy_app, sys_light_api_client, is_lapp, expected):
        with legacy_db.session_scope() as session:
            AppAdaptor(session).update(code=legacy_app.code, data={"is_lapp": is_lapp})

        response = sys_light_api_client.get(
            "/sys/api/light-applications/?light_app_code=" + legacy_app.code,
        )
        assert response.status_code == 200
        result = response.json()

        data = result.pop("data")
        assert result.pop("bk_error_msg") == expected.pop("bk_error_msg").format(code=legacy_app.code)
        if expected["result"]:
            assert data
        assert result == expected

    @pytest.mark.parametrize(
        ("is_lapp", "data", "expected"),
        [
            (False, {}, {"bk_error_msg": "{code} not found", "bk_error_code": "1301100", "result": False, "data": ""}),
            (
                True,
                {"app_name": "Bar", "introduction": "introduction", "developers": ["admin", "blueking"]},
                {
                    "bk_error_msg": "",
                    "bk_error_code": "0",
                    "result": True,
                    "data": {
                        "light_app_code": "{light_app_code}",
                        "app_name": "{app_name}",
                        "introduction": "introduction",
                        "developers": ["admin", "blueking"],
                    },
                },
            ),
            (
                True,
                {
                    "app_name": "Bar",
                    "introduction": "introduction",
                    "developers": ["admin", "blueking"],
                    "app_tag": "",
                },
                {
                    "bk_error_msg": "",
                    "bk_error_code": "0",
                    "result": True,
                    "data": {
                        "light_app_code": "{light_app_code}",
                        "app_name": "{app_name}",
                        "introduction": "introduction",
                        "developers": ["admin", "blueking"],
                    },
                },
            ),
        ],
    )
    def test_edit(self, legacy_tag, legacy_app, sys_light_api_client, is_lapp, data, expected):
        with legacy_db.session_scope() as session:
            AppAdaptor(session).update(code=legacy_app.code, data={"is_lapp": is_lapp})

        data = {
            "light_app_code": legacy_app.code,
            **data,
        }
        if "app_tag" in data:
            data["app_tag"] = legacy_tag.code

        response = sys_light_api_client.patch(
            "/sys/api/light-applications/",
            data=data,
        )
        assert response.status_code == 200

        result = response.json()

        result_data = result.pop("data")
        expected_data = expected.pop("data")
        assert result.pop("bk_error_msg") == expected.pop("bk_error_msg").format(code=legacy_app.code)
        if expected["result"]:
            for k, v in expected_data.items():
                if isinstance(v, str):
                    assert result_data[k] == v.format(**data)
                else:
                    assert result_data[k] == v
        assert result == expected
