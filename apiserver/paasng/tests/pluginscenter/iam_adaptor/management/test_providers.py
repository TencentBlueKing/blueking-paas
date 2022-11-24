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
from bkpaas_auth.core.encoder import ProviderType, user_id_encoder
from django.conf import settings
from django.utils.translation import get_language, override
from django_dynamic_fixture import G
from iam.resource.utils import FancyDict, Page
from translated_fields import to_attribute

from paasng.pluginscenter.iam_adaptor.definitions import gen_iam_resource_id
from paasng.pluginscenter.iam_adaptor.management.providers import PluginProvider
from paasng.pluginscenter.iam_adaptor.models import PluginGradeManager
from paasng.pluginscenter.models import PluginDefinition, PluginInstance
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db


def i18n_name():
    if get_language() == "en":
        return "name" + generate_random_string(length=8)
    else:
        return "名字" + generate_random_string(length=8)


def create_random_plugin(pd: PluginDefinition):
    identifier = generate_random_string()
    return G(
        PluginInstance,
        **{
            "pd": pd,
            "id": identifier,
            to_attribute("name"): i18n_name(),
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


class TestPluginProvider:
    def test_list_attr(self):
        assert PluginProvider().list_attr().to_dict() == {"count": 0, "results": []}

    def test_list_attr_value(self):
        assert PluginProvider().list_attr_value(FancyDict(), Page(0, 0)).to_dict() == {"count": 0, "results": []}

    def test_list_instance_by_policy(self):
        assert PluginProvider().list_instance_by_policy(FancyDict(), Page(0, 0)).to_dict() == {
            "count": 0,
            "results": [],
        }

    def test_list_instance(self, pd):
        with override("zh-cn"):
            p1 = create_random_plugin(pd)
        with override("en"):
            p2 = create_random_plugin(pd)

        provider = PluginProvider()

        with override("zh-cn"):
            assert provider.list_instance(FancyDict(), Page(5, 0)).to_dict() == {
                "count": 2,
                "results": [
                    {"id": gen_iam_resource_id(p1), "display_name": f"{p1.name_zh_cn}({p1.id})"},
                    {"id": gen_iam_resource_id(p2), "display_name": f"{p2.name_zh_cn}({p2.id})"},
                ],
            }
            assert provider.list_instance(FancyDict(), Page(1, 1)).to_dict() == {
                "count": 2,
                "results": [{"id": gen_iam_resource_id(p2), "display_name": f"{p2.name_zh_cn}({p2.id})"}],
            }

        with override("en"):
            assert provider.list_instance(FancyDict(), Page(5, 0)).to_dict() == {
                "count": 2,
                "results": [
                    {"id": gen_iam_resource_id(p1), "display_name": f"{p1.name_en}({p1.id})"},
                    {"id": gen_iam_resource_id(p2), "display_name": f"{p2.name_en}({p2.id})"},
                ],
            }
            assert provider.list_instance(FancyDict(), Page(1, 1)).to_dict() == {
                "count": 2,
                "results": [{"id": gen_iam_resource_id(p2), "display_name": f"{p2.name_en}({p2.id})"}],
            }

    def test_fetch_instance_info(self, pd, iam_management_client):
        with override("zh-cn"):
            p1 = create_random_plugin(pd)
        with override("en"):
            p2 = create_random_plugin(pd)

        G(PluginGradeManager, pd_id=p1.pd.identifier, plugin_id=p1.id, grade_manager_id=1)
        G(PluginGradeManager, pd_id=p2.pd.identifier, plugin_id=p2.id, grade_manager_id=2)

        provider = PluginProvider()
        with override("en"):
            assert provider.fetch_instance_info(FancyDict({"ids": [gen_iam_resource_id(p1)]})).to_dict() == {
                "count": 1,
                "results": [
                    {
                        "id": gen_iam_resource_id(p1),
                        "display_name": f"{p1.name_en}({p1.id})",
                        "_bk_iam_approver_": ["admin", "test"],
                    },
                ],
            }
            assert provider.fetch_instance_info(
                FancyDict({"ids": [gen_iam_resource_id(p1), gen_iam_resource_id(p2)]})
            ).to_dict() == {
                "count": 2,
                "results": [
                    {
                        "id": gen_iam_resource_id(p1),
                        "display_name": f"{p1.name_en}({p1.id})",
                        "_bk_iam_approver_": ["admin", "test"],
                    },
                    {
                        "id": gen_iam_resource_id(p2),
                        "display_name": f"{p2.name_en}({p2.id})",
                        "_bk_iam_approver_": ["admin", "test"],
                    },
                ],
            }
