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
from unittest import mock

import pytest
from django_dynamic_fixture import G
from translated_fields import to_attribute

from paasng.pluginscenter.constants import PluginRole
from paasng.pluginscenter.models import (
    PluginBasicInfoDefinition,
    PluginDefinition,
    PluginInstance,
    PluginMarketInfoDefinition,
    PluginMembership,
)
from tests.utils.helpers import generate_random_string


def make_api_resource(path: str = ""):
    return {"apiName": "dummy", "path": path, "method": "GET"}


@pytest.fixture
def pd():
    pd: PluginDefinition = G(
        PluginDefinition,
        **{
            "identifier": generate_random_string(),
            to_attribute("name"): generate_random_string(),
            "administrator": [],
            "approval_config": {},
            "release_revision": {"revisionType": "master", "versionNo": "automatic"},
            "release_stages": [],
        },
    )
    pd.market_info_definition = G(
        PluginMarketInfoDefinition,
        pd=pd,
        api={
            "create": make_api_resource("create-market"),
            "read": make_api_resource("read-market-{ plugin_id }"),
            "update": make_api_resource("update-market-{ plugin_id }"),
        },
        category=make_api_resource("list-category"),
    )
    pd.basic_info_definition = G(
        PluginBasicInfoDefinition,
        pd=pd,
        id_schema={
            "pattern": "^[a-z0-9-]{1,16}$",
            "description": "由小写字母、数字、连字符(-)组成，长度小于 16 个字符",
        },
        name_schema={
            "pattern": r"[\\u4300-\\u9fa5\\w\\d\\-_]{1,20}",
            "description": "由汉字、英文字母、数字组成，长度小于 20 个字符",
        },
        init_templates=[
            {"id": "foo", "name": "Foo Template", "language": "Python", "repository": "https://example.com/foo"},
            {"id": "bar", "name": "Bar Template", "language": "Java", "repository": "https://example.com/bar"},
        ],
        extra_fields={
            "email": {
                "pattern": r"[\w'.%+-]+@(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,4}",
                "description": "电子邮箱",
            }
        },
        api={
            "create": make_api_resource("create-instance"),
            "update": make_api_resource("update-instance-{ plugin_id }"),
            "delete": make_api_resource("delete-instance-{ plugin_id }"),
        },
    )
    pd.save()
    pd.refresh_from_db()
    return pd


@pytest.fixture
def mock_client():
    with mock.patch("paasng.pluginscenter.thirdparty.utils.DynamicClient") as cls:
        yield cls().with_group().with_bkapi_authorization().group


@pytest.fixture
def plugin(pd, bk_user):
    identifier = generate_random_string()
    plugin: PluginInstance = G(
        PluginInstance,
        **{
            "pd": pd,
            "id": identifier,
            to_attribute("name"): generate_random_string(),
            "template": {
                "id": "foo",
                "name": "bar",
                "language": "Python",
                "repository": "http://git.example.com/template.git",
            },
            "repo_type": "git",
            "repository": f"http://git.example.com/foo/{identifier}.git",
        },
    )
    G(PluginMembership, plugin=plugin, user=bk_user.pk, role=PluginRole.ADMINISTRATOR)
    return plugin
