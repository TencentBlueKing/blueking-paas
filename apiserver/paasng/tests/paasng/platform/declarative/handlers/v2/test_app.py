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
import io
import json
from textwrap import dedent
from unittest import mock

import cattr
import pytest
from blue_krill.contextlib import nullcontext as does_not_raise

from paasng.platform.applications.constants import AppLanguage
from paasng.platform.applications.models import Application
from paasng.platform.declarative.constants import AppDescPluginType, AppSpecVersion
from paasng.platform.declarative.deployment.env_vars import get_desc_env_variables
from paasng.platform.declarative.deployment.svc_disc import get_services_as_env_variables
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.handlers import AppDescriptionHandler, get_desc_handler
from paasng.platform.smart_app.detector import SourcePackageStatReader
from paasng.platform.sourcectl.utils import generate_temp_file
from tests.paasng.platform.sourcectl.packages.utils import gen_tar

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestAppDescriptionHandler:
    def test_empty_file(self, bk_user):
        fp = io.StringIO("")
        with pytest.raises(DescriptionValidationError):
            AppDescriptionHandler.from_file(fp).handle_app(bk_user)

    def test_app_normal(self, random_name, bk_user, one_px_png):
        fp = io.StringIO(
            dedent(
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
        )

        application = AppDescriptionHandler.from_file(fp).handle_app(bk_user)

        assert application is not None
        assert Application.objects.filter(code=random_name).exists()
        # 由于 ProcessedImageField 会将 logo 扩展为 144,144, 因此这里判断对应的位置的标记位
        logo_content = application.logo.read()
        assert logo_content[19] == 144
        assert logo_content[23] == 144

    def test_app_from_stat(self, random_name, bk_user, one_px_png):
        fp = io.StringIO(
            dedent(
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
        )

        with generate_temp_file() as file_path:
            gen_tar(
                file_path,
                {
                    "./foo/app_desc.yaml": fp.read(),
                    "./foo/logo.png": one_px_png,
                },
            )
            stat = SourcePackageStatReader(file_path).read()
            application = AppDescriptionHandler(stat.meta_info).handle_app(bk_user)

            assert application is not None
            assert Application.objects.filter(code=random_name).exists()
            # 由于 ProcessedImageField 会将 logo 扩展为 144,144, 因此这里判断对应的位置的标记位
            logo_content = application.logo.read()
            assert logo_content[19] == 144
            assert logo_content[23] == 144

    @pytest.mark.parametrize(
        ("yaml_content", "ctx"),
        [
            (
                dedent(
                    """
                spec_version: 2
                module:
                    env_variables:
                        - key: FOO
                          value: 1
                    language: python
                    svc_discovery:
                        bk_saas:
                        - foo-app
                        - bk_app_code: bar-app
                          module_name: api
                    bkmonitor:
                        port: 80
                """
                ),
                does_not_raise(
                    {
                        "env_variables": {"FOO": "1"},
                        "svc_discovery": {
                            "BKPAAS_SERVICE_ADDRESSES_BKSAAS": base64.b64encode(
                                json.dumps(
                                    [
                                        {
                                            "key": {"bk_app_code": "foo-app", "module_name": None},
                                            "value": {
                                                "stag": "http://stag-dot-foo-app.bkapps.example.com",
                                                "prod": "http://foo-app.bkapps.example.com",
                                            },
                                        },
                                        {
                                            "key": {"bk_app_code": "bar-app", "module_name": "api"},
                                            "value": {
                                                "stag": "http://stag-dot-api-dot-bar-app.bkapps.example.com",
                                                "prod": "http://prod-dot-api-dot-bar-app.bkapps.example.com",
                                            },
                                        },
                                    ]
                                ).encode()
                            ).decode()
                        },
                        "bk_monitor": {
                            "port": 80,
                            "target_port": 80,
                        },
                    }
                ),
            ),
            (
                dedent(
                    """
                    version: 1
                    module:
                        language: python
                        env_variables:
                            - key: BKPAAS_RESERVED_KEY
                              value: raise error
                    """
                ),
                pytest.raises(DescriptionValidationError),
            ),
        ],
    )
    def test_deployment_normal(self, bk_deployment, yaml_content, ctx):
        fp = io.StringIO(yaml_content)
        with ctx as expected, mock.patch(
            "paasng.platform.declarative.handlers.DeploymentDeclarativeController.update_bkmonitor"
        ) as update_bkmonitor:
            AppDescriptionHandler.from_file(fp).handle_deployment(bk_deployment)
            assert get_desc_env_variables(bk_deployment) == expected["env_variables"]
            assert get_services_as_env_variables(bk_deployment) == expected["svc_discovery"]
            assert update_bkmonitor.called
            assert cattr.unstructure(update_bkmonitor.call_args[0][0]) == expected["bk_monitor"]


def test_app_data_to_desc(random_name):
    app_data = {
        "spec_version": AppSpecVersion.VER_2,
        "app_version": "0.0.1",
        "app": {"bk_app_code": random_name, "bk_app_name": random_name},
        "modules": {"default": {"is_default": True, "language": "python"}},
    }

    desc = get_desc_handler(app_data).app_desc
    assert desc.name_zh_cn == random_name
    assert desc.code == random_name
    plugin = desc.get_plugin(AppDescPluginType.APP_VERSION)
    assert plugin
    assert plugin["data"] == "0.0.1"
    assert desc.default_module.language == AppLanguage.PYTHON
