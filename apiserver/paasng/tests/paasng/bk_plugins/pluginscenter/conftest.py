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
import string
from unittest import mock

import pytest
from bkpaas_auth.core.encoder import ProviderType, user_id_encoder
from django.conf import settings
from django_dynamic_fixture import G
from translated_fields import to_attribute

from paasng.bk_plugins.pluginscenter.constants import MarketInfoStorageType, PluginReleaseMethod, PluginRole
from paasng.bk_plugins.pluginscenter.iam_adaptor.models import PluginGradeManager, PluginUserGroup
from paasng.bk_plugins.pluginscenter.iam_adaptor.policy.client import BKIAMClient
from paasng.bk_plugins.pluginscenter.itsm_adaptor.constants import ApprovalServiceName
from paasng.bk_plugins.pluginscenter.models import (
    ApprovalService,
    PluginBasicInfoDefinition,
    PluginConfigInfoDefinition,
    PluginDefinition,
    PluginInstance,
    PluginMarketInfoDefinition,
    PluginRelease,
    PluginReleaseStage,
)
from paasng.infras.accounts.constants import AccountFeatureFlag as AFF
from paasng.infras.accounts.models import AccountFeatureFlag
from tests.utils.helpers import generate_random_string


def make_api_resource(path: str = ""):
    return {"apiName": "dummy", "path": path, "method": "GET"}


@pytest.fixture
def pd():
    log_params = {"indexPattern": "", "termTemplate": {}}
    pd: PluginDefinition = G(
        PluginDefinition,
        identifier=generate_random_string(),
        administrator=[],
        approval_config={},
        release_revision={
            "revisionType": "master",
            "versionNo": "automatic",
            "api": {
                "create": make_api_resource("create-release"),
                "update": make_api_resource("update-release-{ version_id }"),
            },
        },
        release_stages=[{"id": "online_approval", "name": "上线审批", "invokeMethod": "itsm"}],
        log_config={
            "backendType": "es",
            "stdout": log_params,
            "json": log_params,
            "ingress": log_params,
        },
        **{to_attribute("name"): generate_random_string()},
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
        storage=MarketInfoStorageType.PLATFORM,
    )
    pd.basic_info_definition = G(
        PluginBasicInfoDefinition,
        pd=pd,
        release_method=PluginReleaseMethod.CODE,
        id_schema={
            "title": "插件ID",
            "pattern": "^[a-z0-9-]{1,16}$",
            "description": "由小写字母、数字、连字符(-)组成，长度小于 16 个字符",
            "maxlength": 10,
        },
        name_schema={
            "title": "插件名称",
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
            },
            "distributor_codes": {
                "title": "插件使用方",
                "type": "array",
                "items": {"type": "string"},
                "ui:component": {
                    "name": "select",
                    "props": {
                        "remoteConfig": {"url": "/api/bk_plugin_distributors/", "label": "name", "value": "code_name"},
                    },
                },
            },
        },
        api={
            "create": make_api_resource("create-instance"),
            "update": make_api_resource("update-instance-{ plugin_id }"),
            "delete": make_api_resource("delete-instance-{ plugin_id }"),
        },
    )

    pd.config_definition = G(
        PluginConfigInfoDefinition,
        pd=pd,
        title_zh_cn="配置管理",
        sync_api=make_api_resource("sync-configuration-{ plugin_id }"),
        columns=[
            {"type": "string", "title": "FOO", "unique": True, "name": "FOO"},
            {"type": "string", "title": "BAR", "unique": False, "name": "BAR"},
        ],
    )
    pd.save()
    pd.refresh_from_db()
    return pd


@pytest.fixture
def plugin(pd, bk_user):
    identifier = generate_random_string(length=10, chars=string.ascii_lowercase)
    plugin: PluginInstance = G(
        PluginInstance,
        **{
            "pd": pd,
            "id": identifier,
            to_attribute("name"): generate_random_string(length=20, chars=string.ascii_lowercase),
            "template": {
                "id": "foo",
                "name": "bar",
                "language": "Python",
                "repository": "http://git.example.com/template.git",
            },
            "repo_type": "git",
            "repository": f"http://git.example.com/foo/{identifier}.git",
            "creator": user_id_encoder.encode(getattr(ProviderType, settings.BKAUTH_DEFAULT_PROVIDER_TYPE), "admin"),
        },
    )
    plugin.refresh_from_db()
    return plugin


@pytest.fixture
def plugin_with_role(plugin):
    # 初始化成员信息
    G(PluginGradeManager, pd_id=plugin.pd.identifier, plugin_id=plugin.id, grade_manager_id=1)
    G(PluginUserGroup, pd_id=plugin.pd.identifier, plugin_id=plugin.id, role=PluginRole.ADMINISTRATOR, user_group_id=1)
    G(PluginUserGroup, pd_id=plugin.pd.identifier, plugin_id=plugin.id, role=PluginRole.DEVELOPER, user_group_id=2)
    return plugin


@pytest.fixture
def release(plugin):
    release: PluginRelease = G(
        PluginRelease,
        plugin=plugin,
        source_location=plugin.repository,
        type="prod",
        source_version_type="branch",
        source_version_name="master",
        version="0.0.1",
        comment="",
    )
    release.initial_stage_set()
    return release


@pytest.fixture
def itsm_online_stage(release):
    stage = PluginReleaseStage.objects.filter(
        release=release, invoke_method="itsm", stage_id="online_approval"
    ).first()
    return stage


@pytest.fixture
def online_approval_service():
    svc: ApprovalService = G(ApprovalService, service_name=ApprovalServiceName.ONLINE_APPROVAL.value, service_id=1)
    return svc


@pytest.fixture
def thirdparty_client():
    with mock.patch("paasng.bk_plugins.pluginscenter.thirdparty.utils.DynamicClient") as cls:
        yield cls().with_group().with_bkapi_authorization().with_i18n_hook().group


@pytest.fixture
def iam_policy_client():
    with mock.patch(
        "paasng.bk_plugins.pluginscenter.iam_adaptor.policy.permissions.lazy_iam_client",
        new=mock.MagicMock(),
        spec=BKIAMClient,
    ) as iam_policy_client:
        iam_policy_client.is_action_allowed.return_value = True
        iam_policy_client.is_actions_allowed.return_value = {"": True}
        yield iam_policy_client


@pytest.fixture()
def setup_bk_user(bk_user):
    AccountFeatureFlag.objects.set_feature(bk_user, AFF.ALLOW_PLUGIN_CENTER, True)
