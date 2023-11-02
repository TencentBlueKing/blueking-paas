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
from django_dynamic_fixture import G

from paasng.bk_plugins.pluginscenter.models.instances import PluginRelease
from paasng.bk_plugins.pluginscenter.thirdparty import release as release_api

pytestmark = pytest.mark.django_db


@pytest.fixture
def release_version(plugin) -> PluginRelease:
    return G(
        PluginRelease,
        plugin=plugin,
        version="1,2,3",
        comment="foo",
        semver_type="major",
        extra_fields={"foo": "bar"},
        source_location="https://github.com/TencentBlueKing/blueking-paas",
        source_version_type="branch",
        source_version_name="main",
    )


@pytest.mark.parametrize("handler", (release_api.create_release, release_api.update_release))
def test_release_upsert_api(thirdparty_client, pd, plugin, handler, release_version):
    """测试 ReleaseVersion create/update 接口的序列化"""
    handler(pd, plugin, version=release_version, operator="nobody")
    assert thirdparty_client.call.called is True
    data = thirdparty_client.call.call_args.kwargs["data"]
    assert data["version"] == {
        "type": release_version.type,
        "version": "1,2,3",
        "comment": "foo",
        "semver_type": "major",
        "extra_fields": {"foo": "bar"},
        # 源码信息
        "source_location": "https://github.com/TencentBlueKing/blueking-paas",
        "source_version_type": "branch",
        "source_version_name": "main",
        "source_hash": release_version.source_hash,
    }
    assert data["status"] == release_version.status
    assert data["operator"] == "nobody"
