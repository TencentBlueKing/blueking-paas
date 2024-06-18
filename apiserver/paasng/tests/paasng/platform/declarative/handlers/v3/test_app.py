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
import base64
from textwrap import dedent

import pytest
import yaml

from paasng.platform.applications.constants import AppLanguage
from paasng.platform.applications.models import Application
from paasng.platform.declarative.constants import AppDescPluginType
from paasng.platform.declarative.handlers import CNativeAppDescriptionHandler, DescriptionHandler
from paasng.platform.declarative.handlers import get_desc_handler as _get_desc_handler
from paasng.platform.smart_app.services.detector import SourcePackageStatReader
from paasng.platform.sourcectl.utils import generate_temp_file
from tests.paasng.platform.sourcectl.packages.utils import gen_tar

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def get_desc_handler(yaml_content: str) -> DescriptionHandler:
    handler = _get_desc_handler(yaml.safe_load(yaml_content))
    assert isinstance(handler, CNativeAppDescriptionHandler)
    return handler


class TestCNativeAppDescriptionHandler:
    def test_app_normal(self, random_name, bk_user, one_px_png):
        yaml_content = dedent(
            f"""
        specVersion: 3
        appVersion: 0.0.1
        app:
          bkAppCode: {random_name}
          bkAppName: {random_name}
          market:
              introduction: dummy
              logoB64data: "base64,{base64.b64encode(one_px_png).decode()}"
        modules:
        - name: default
          isDefault: true
          language: python
          spec: {{}}
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
        specVersion: 3
        appVersion: 0.0.1
        app:
          bkAppCode: {random_name}
          bkAppName: {random_name}
          market:
              introduction: dummy
        modules:
        - name: default
          isDefault: true
          language: python
          spec: {{}}
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


def test_app_data_to_desc(random_name):
    app_data = dedent(
        f"""
    specVersion: 3
    appVersion: 0.0.1
    app:
      bkAppCode: {random_name}
      bkAppName: {random_name}
    modules:
    - name: default
      isDefault: true
      language: python
      spec: {{}}
    """
    )

    desc = get_desc_handler(app_data).app_desc
    assert desc.name_zh_cn == random_name
    assert desc.code == random_name
    plugin = desc.get_plugin(AppDescPluginType.APP_VERSION)
    assert plugin
    assert plugin["data"] == "0.0.1"
    assert desc.default_module.language == AppLanguage.PYTHON
