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
from hashlib import sha256

import pytest
from django_dynamic_fixture import G

from paasng.bk_plugins.pluginscenter.configuration import PluginConfigManager
from paasng.bk_plugins.pluginscenter.models import PluginConfig

pytestmark = pytest.mark.django_db


class TestPluginConfigManager:
    @pytest.fixture()
    def mgr(self, pd, plugin):
        return PluginConfigManager(pd, plugin)

    def test_create(self, plugin, mgr):
        assert PluginConfig.objects.filter(plugin=plugin).count() == 0
        config = mgr.save({"FOO": "foo", "BAR": "bar"})
        assert PluginConfig.objects.filter(plugin=plugin).count() == 1
        assert config.unique_key == sha256(b"foo").hexdigest()
        assert config.row == {"FOO": "foo", "BAR": "bar"}

    def test_update(self, plugin, mgr):
        config = G(PluginConfig, plugin=plugin, unique_key=sha256(b"foo").hexdigest(), row={"FOO": "foo"})
        mgr.save({"FOO": "foo", "BAR": "bar", "__id__": sha256(b"foo").hexdigest()})

        config.refresh_from_db()
        assert PluginConfig.objects.filter(plugin=plugin).count() == 1
        assert config.row == {"FOO": "foo", "BAR": "bar"}

    def test_create_new_one(self, plugin, mgr):
        old_config = G(PluginConfig, plugin=plugin, unique_key=sha256(b"foo").hexdigest(), row={"FOO": "foo"})
        mgr.save({"FOO": "not-foo", "BAR": "bar", "__id__": sha256(b"foo").hexdigest()})

        assert PluginConfig.objects.filter(plugin=plugin).count() == 1
        new_config = PluginConfig.objects.get(plugin=plugin)
        assert old_config.pk != new_config.pk
        assert new_config.row == {"FOO": "not-foo", "BAR": "bar"}

    def test_delete(self, plugin, mgr):
        config = mgr.save({"FOO": "foo", "BAR": "bar"})
        assert PluginConfig.objects.filter(plugin=plugin).count() == 1
        mgr.delete(config.unique_key)
        assert PluginConfig.objects.filter(plugin=plugin).count() == 0
