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
import requests

from paasng.bk_plugins.pluginscenter.constants import PluginStatus
from paasng.bk_plugins.pluginscenter.thirdparty import instance

pytestmark = pytest.mark.django_db


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
