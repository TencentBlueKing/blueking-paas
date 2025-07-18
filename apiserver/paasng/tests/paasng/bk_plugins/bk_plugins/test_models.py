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

from functools import partial

import pytest
from django_dynamic_fixture import G

from paasng.bk_plugins.bk_plugins.apigw import set_distributors
from paasng.bk_plugins.bk_plugins.constants import PluginTagIdType
from paasng.bk_plugins.bk_plugins.models import (
    BkPlugin,
    BkPluginAppQuerySet,
    BkPluginDistributor,
    BkPluginProfile,
    BkPluginTag,
    get_deployed_statuses,
    get_plugin_env_variables,
    make_bk_plugin,
    plugin_to_detailed,
)
from paasng.core.tenant.user import DEFAULT_TENANT_ID
from paasng.platform.applications.constants import ApplicationType

pytestmark = pytest.mark.django_db


class TestBkPlugin:
    def test_from_application(self, bk_plugin_app):
        obj = BkPlugin.from_application(bk_plugin_app)
        assert obj.id == bk_plugin_app.id.hex


@pytest.mark.usefixtures("_with_empty_live_addrs")
def test_get_deployed_statuses(bk_plugin_app):
    obj = BkPlugin.from_application(bk_plugin_app)
    assert get_deployed_statuses(obj) is not None


def test_make_bk_plugin_normal(bk_app):
    bk_app.is_plugin_app = True
    assert make_bk_plugin(bk_app) is not None, 'should succeed for "bk_plugin" type'


def test_make_bk_plugin_wrong_type(bk_app):
    bk_app.type = ApplicationType.DEFAULT
    with pytest.raises(TypeError):
        make_bk_plugin(bk_app)


def test_get_or_create_by_application(bk_app):
    profile, _ = BkPluginProfile.objects.get_or_create_by_application(bk_app)
    assert profile.contact, "contact should set to initial value"
    assert profile.tag is None

    tag_1 = G(BkPluginTag, code_name="sample-tag-code-1", name="sample-tag-1")
    profile.tag = tag_1
    assert profile.tag.name == "sample-tag-1"


@pytest.mark.usefixtures("_with_empty_live_addrs")
def test_plugin_to_detailed_default(bk_plugin):
    ret = plugin_to_detailed(bk_plugin)
    assert ret.dict()["deployed_statuses"]["stag"].get("addresses") is not None


@pytest.mark.usefixtures("_with_empty_live_addrs")
def test_plugin_to_detailed_no_addresses(bk_plugin):
    ret = plugin_to_detailed(bk_plugin, include_addresses=False)
    assert ret.dict()["deployed_statuses"]["stag"].get("addresses") is None


def test_get_plugin_env_variables(bk_plugin):
    """Test the normal case"""
    env = bk_plugin.get_application().default_module.get_envs("prod")
    profile = bk_plugin.get_profile()
    profile.api_gw_name = "foo"
    profile.save(update_fields=["api_gw_name"])
    assert get_plugin_env_variables(env).kv_map == {"BKPAAS_BK_PLUGIN_APIGW_NAME": "foo"}


class TestBkPluginAppQuerySet:
    def test_distributor_code_name(self, bk_plugin_app, mock_apigw_api_client):
        query = partial(
            BkPluginAppQuerySet().filter, search_term="", order_by=["-created"], tenant_id=DEFAULT_TENANT_ID
        )
        assert query().count() == 1
        assert query(distributor_code_name="sample-dis-1").count() == 0

        # Grant permissions on distributor and query again
        dis_1 = G(BkPluginDistributor, code_name="sample-dis-1", bk_app_code="sample-dis-1")
        set_distributors(bk_plugin_app, [dis_1])
        assert query(distributor_code_name="sample-dis-1").count() == 1

    def test_tag_id(self, bk_plugin, mock_apigw_api_client):
        query = partial(
            BkPluginAppQuerySet().filter, search_term="", order_by=["-created"], tenant_id=DEFAULT_TENANT_ID
        )

        tag_1 = G(BkPluginTag, code_name="sample-tag-1", name="sample-tag-1")
        assert query(tag_id=tag_1.id).count() == 0

        # When the plugin is not bound to the tag,
        # you can filter the unclassified plugins according to "UNTAGGED TAG ID"
        assert query(tag_id=PluginTagIdType.UNTAGGED.value).count() == 1

        # Add tag to plugin and query again
        profile = bk_plugin.get_profile()
        profile.tag = tag_1
        profile.save(update_fields=["tag"])
        assert query(tag_id=tag_1.id).count() == 1

    def test_tenant_id(self, bk_plugin_app, mock_apigw_api_client):
        default_query = partial(
            BkPluginAppQuerySet().filter, search_term="", order_by=["-created"], tenant_id=DEFAULT_TENANT_ID
        )
        assert default_query().count() == 1
        tenant1_query = partial(
            BkPluginAppQuerySet().filter, search_term="", order_by=["-created"], tenant_id="tenant1"
        )
        assert tenant1_query().count() == 0

        bk_plugin_app.tenant_id = "tenant1"
        bk_plugin_app.save()
        assert BkPluginAppQuerySet().filter(search_term="", order_by=["-created"], tenant_id="tenant1").count() == 1
