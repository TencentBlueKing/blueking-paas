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
import json
from typing import Dict
from unittest import mock

import pytest
import requests
from bkapi_client_core.exceptions import ResponseError
from blue_krill.web.std_error import APIError
from django.conf import settings
from django_dynamic_fixture import G
from requests.models import Response
from translated_fields import to_attribute

from paasng.bk_plugins.pluginscenter.constants import PluginStatus
from paasng.bk_plugins.pluginscenter.models import PluginMarketInfo
from paasng.bk_plugins.pluginscenter.serializers import PluginMarketInfoSLZ
from paasng.bk_plugins.pluginscenter.thirdparty import instance, market
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db


@pytest.fixture
def market_info(plugin):
    return G(
        PluginMarketInfo,
        **{
            "plugin": plugin,
            to_attribute("introduction"): generate_random_string(),
            to_attribute("description"): generate_random_string(),
            "contact": "a;b;c;",
        },
    )


@pytest.fixture
def thirdparty_client_session():
    with mock.patch("bkapi_client_core.session.Session.request") as mocked_request:
        yield mocked_request


@pytest.mark.parametrize("handler", (instance.create_instance, instance.update_instance))
def test_instance_upsert_api(thirdparty_client, pd, plugin, handler):
    """测试 instance create/update 接口的序列化"""
    handler(pd, plugin, operator="nobody")
    assert thirdparty_client.call.called is True
    data = thirdparty_client.call.call_args.kwargs["data"]
    # 验证国际化字段存在
    assert (
        data.keys() ^ {"id", "name_zh_cn", "name_en", "template", "extra_fields", "repository", "operator", "logo_url"}
        == set()
    )
    assert data["template"] == {
        "id": "foo",
        "name": "bar",
        "language": "Python",
        "applicable_language": None,
        "repository": "http://git.example.com/template.git",
    }
    assert data["repository"] == f"http://git.example.com/foo/{data['id']}.git"
    assert data["operator"] == "nobody"


def test_instance_delete_api(thirdparty_client_session, pd, plugin):
    response = requests.Response()
    response.status_code = 200
    response._content = b"{}"
    thirdparty_client_session.return_value = response
    instance.archive_instance(pd, plugin, "")
    assert thirdparty_client_session.called
    assert f"delete-instance-{plugin.id}" in thirdparty_client_session.call_args.kwargs["url"]
    plugin.refresh_from_db()
    assert plugin.status in PluginStatus.archive_status()


@pytest.mark.parametrize("handler", (market.create_market_info, market.update_market_info))
def test_market_upsert_api(thirdparty_client, pd, plugin, market_info, handler):
    """测试 market create/update 接口的序列化"""
    handler(pd, plugin, market_info, operator="nobody")
    assert thirdparty_client.call.called is True
    data = thirdparty_client.call.call_args.kwargs["data"]
    # 验证国际化字段存在
    assert (
        data.keys()
        ^ {
            "category",
            "contact",
            "extra_fields",
            "introduction_zh_cn",
            "introduction_en",
            "description_zh_cn",
            "description_en",
            "operator",
        }
        == set()
    )
    assert data["operator"] == "nobody"


def test_market_read_api(thirdparty_client, pd, plugin):
    data = {
        "category": "foo",
        "introduction": "introduction",
        **{to_attribute("description", language_code=language[0]): language[0] for language in settings.LANGUAGES},
        "extra_fields": {"foo": "foo"},
        "contact": "a;b;c;",
    }
    thirdparty_client.call.return_value = data
    info = market.read_market_info(pd, plugin)
    dumped = PluginMarketInfoSLZ(info).data
    assert dumped["category"] == "foo"
    assert dumped["introduction"] == "introduction"
    assert dumped["description"] == "zh-cn"
    assert dumped["extra_fields"] == {"foo": "foo"}
    assert dumped["contact"] == "a;b;c;"


def make_response(data: Dict) -> Response:
    response = Response()
    response._content = json.dumps(data).encode()
    response.status_code = 400
    return response


@pytest.mark.parametrize(
    "exception, expected_exception",
    [
        (Exception(), APIError(code="UnknownError", message="system error")),
        (ResponseError(response=make_response({})), APIError(code="APIError", message="[invalid response body]")),
        (ResponseError(response=make_response({"message": "错误信息"})), APIError(code="APIError", message="错误信息")),
        (
            ResponseError(
                response=make_response({"message": "错误信息"}),
                response_headers_representer=mock.MagicMock(request_id="foo"),
            ),
            APIError(code="APIError", message="<request_id: foo> 错误信息"),
        ),
        (
            ResponseError(
                response=make_response({"detail": "错误信息"}),
                response_headers_representer=mock.MagicMock(request_id="foo"),
            ),
            APIError(code="APIError", message="<request_id: foo> 错误信息"),
        ),
    ],
)
def test_transform_exception(pd, plugin, exception, expected_exception):
    with mock.patch("bkapi_client_core.base.Operation.__call__") as call:
        call.side_effect = exception
        with pytest.raises(APIError) as exc:
            market.read_market_info(pd, plugin)
        assert exc.value.code == expected_exception.code
        assert exc.value.message == expected_exception.message
        assert exc.value.code_num == expected_exception.code_num
