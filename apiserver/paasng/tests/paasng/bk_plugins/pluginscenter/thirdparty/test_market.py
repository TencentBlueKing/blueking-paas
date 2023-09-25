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
from django.conf import settings
from django_dynamic_fixture import G
from translated_fields import to_attribute

from paasng.bk_plugins.pluginscenter.models import PluginMarketInfo
from paasng.bk_plugins.pluginscenter.serializers import PluginMarketInfoSLZ
from paasng.bk_plugins.pluginscenter.thirdparty import market
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
