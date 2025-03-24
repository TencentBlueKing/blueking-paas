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

import base64
from textwrap import dedent, indent

import pytest
import yaml
from django_dynamic_fixture import G

from paas_wl.infras.cluster.models import Cluster
from paasng.core.tenant.constants import AppTenantMode
from paasng.platform.applications.constants import AppLanguage
from paasng.platform.applications.models import Application
from paasng.platform.declarative.constants import AppDescPluginType
from paasng.platform.declarative.handlers import AppDescriptionHandler, DescriptionHandler
from paasng.platform.declarative.handlers import get_desc_handler as _get_desc_handler
from paasng.platform.modules.helpers import get_module_clusters
from paasng.platform.smart_app.services.detector import SourcePackageStatReader
from paasng.platform.sourcectl.utils import generate_temp_file
from tests.paasng.platform.sourcectl.packages.utils import gen_tar
from tests.utils.basic import generate_random_string

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def get_desc_handler(yaml_content: str) -> DescriptionHandler:
    meta_info = yaml.safe_load(yaml_content)
    meta_info["tenant"] = {"app_tenant_mode": AppTenantMode.GLOBAL, "app_tenant_id": "", "tenant_id": "test_id"}
    handler = _get_desc_handler(meta_info)
    assert isinstance(handler, AppDescriptionHandler)
    return handler


class TestAppDescriptionHandler:
    def test_app_normal(self, random_name, bk_user, one_px_png):
        yaml_content = dedent(
            f"""
        spec_version: 2
        app:
            bk_app_code: {random_name}
            bk_app_name: {random_name}
            market:
              introduction: dummy
              logo_b64data: "base64,{base64.b64encode(one_px_png).decode()}"
        modules:
            default:
                is_default: true
                language: python
        """
        )

        application = get_desc_handler(yaml_content).handle_app(bk_user)

        assert application is not None
        assert Application.objects.filter(code=random_name).exists()
        # 由于 ProcessedImageField 会将 logo 扩展为 144,144, 因此这里判断对应的位置的标记位
        logo_content = application.logo.read()
        assert logo_content[19] == 144
        assert logo_content[23] == 144

    def test_app_from_stat(self, random_name, bk_user, one_px_png):
        yaml_content = dedent(
            f"""
        spec_version: 2
        app:
            bk_app_code: {random_name}
            bk_app_name: {random_name}
            market:
              introduction: dummy
        modules:
            default:
                is_default: true
                language: python
        """
        )

        with generate_temp_file() as file_path:
            gen_tar(
                file_path,
                {
                    "./foo/app_desc.yaml": yaml_content,
                    "./foo/logo.png": one_px_png,
                },
            )
            stat = SourcePackageStatReader(file_path).read()
            application = get_desc_handler(yaml.dump(stat.meta_info)).handle_app(bk_user)

            assert application is not None
            assert Application.objects.filter(code=random_name).exists()
            # 由于 ProcessedImageField 会将 logo 扩展为 144,144, 因此这里判断对应的位置的标记位
            logo_content = application.logo.read()
            assert logo_content[19] == 144
            assert logo_content[23] == 144


class TestAppNewModuleUseRightCluster:
    def test_integrated(self, random_name, bk_user):
        """When creating a new module for an existing application, the module should use
        the same cluster as the existing default module instead of the default cluster configured globally.
        """
        # Create the application with a default module. the module will be bound to the default
        # cluster after the creation.
        yaml_content = dedent(
            f"""
        spec_version: 2
        app:
            bk_app_code: {random_name}
            bk_app_name: {random_name}
        modules:
            default:
                is_default: true
                language: python"""
        )
        get_desc_handler(yaml_content).handle_app(bk_user)

        # Create a new cluster and make it the new default
        old_default_cluster = Cluster.objects.get(is_default=True)
        new_cluster = G(Cluster, name=generate_random_string(6), is_default=False)
        Cluster.objects.switch_default_cluster(new_cluster.name)

        # Create a new module called "new" by handle the modified YAML again
        yaml_content_new_module = yaml_content + indent(
            dedent(
                """
        new:
            language: python
        """
            ),
            prefix="    ",
        )
        app = get_desc_handler(yaml_content_new_module).handle_app(bk_user)

        # Do the assertions
        new_module_clusters = get_module_clusters(app.get_module("new"))
        new_module_cluster = list(new_module_clusters.values())[0]
        assert new_module_cluster.name == old_default_cluster.name
        assert get_module_clusters(app.get_default_module()) == new_module_clusters, (
            "The new module should use the same cluster as the default one."
        )


def test_app_data_to_desc(random_name):
    app_data = dedent(
        f"""
    spec_version: 2
    app_version: 0.0.1
    app:
        bk_app_code: {random_name}
        bk_app_name: {random_name}
    modules:
        default:
            is_default: True
            language: python
    """
    )

    desc = get_desc_handler(app_data).app_desc
    assert desc.name_zh_cn == random_name
    assert desc.code == random_name
    plugin = desc.get_plugin(AppDescPluginType.APP_VERSION)
    assert plugin
    assert plugin["data"] == "0.0.1"
    assert desc.default_module.language == AppLanguage.PYTHON
