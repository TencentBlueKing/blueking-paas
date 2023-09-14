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
from typing import Dict
from unittest import mock

import cattr
import pytest
from blue_krill.contextlib import nullcontext as does_not_raise

from paasng.dev_resources.sourcectl.utils import generate_temp_file
from paasng.extensions.declarative.application.resources import ServiceSpec
from paasng.extensions.declarative.constants import AppDescPluginType, AppSpecVersion
from paasng.extensions.declarative.deployment.env_vars import EnvVariablesReader, get_desc_env_variables
from paasng.extensions.declarative.deployment.svc_disc import get_services_as_env_variables
from paasng.extensions.declarative.exceptions import DescriptionValidationError
from paasng.extensions.declarative.handlers import AppDescriptionHandler, SMartDescriptionHandler, get_desc_handler
from paasng.extensions.declarative.models import DeploymentDescription
from paasng.extensions.smart_app.detector import SourcePackageStatReader
from paasng.platform.applications.constants import AppLanguage
from paasng.platform.applications.models import Application
from paasng.publish.market.models import Product
from tests.sourcectl.packages.utils import gen_tar

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestAppDescriptionHandler:
    def test_empty_file(self, bk_user):
        fp = io.StringIO('')
        with pytest.raises(DescriptionValidationError):
            AppDescriptionHandler.from_file(fp).handle_app(bk_user)

    def test_app_normal(self, random_name, bk_user, one_px_png):
        fp = io.StringIO(
            dedent(
                f'''
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
        '''
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
                f'''
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
        '''
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
        "yaml_content, ctx",
        [
            (
                dedent(
                    '''
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
                '''
                ),
                does_not_raise(
                    {
                        "env_variables": {"FOO": "1"},
                        "svc_discovery": {
                            'BKPAAS_SERVICE_ADDRESSES_BKSAAS': base64.b64encode(
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
                                            "key": {"bk_app_code": "bar-app", "module_name": 'api'},
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
                    '''
                    version: 1
                    module:
                        language: python
                        env_variables:
                            - key: BKPAAS_RESERVED_KEY
                              value: raise error
                    '''
                ),
                pytest.raises(DescriptionValidationError),
            ),
        ],
    )
    def test_deployment_normal(self, bk_deployment, yaml_content, ctx):
        fp = io.StringIO(yaml_content)
        with ctx as expected, mock.patch(
            "paasng.extensions.declarative.handlers.DeploymentDeclarativeController.update_bkmonitor"
        ) as update_bkmonitor:
            AppDescriptionHandler.from_file(fp).handle_deployment(bk_deployment)
            assert get_desc_env_variables(bk_deployment) == expected["env_variables"]
            assert get_services_as_env_variables(bk_deployment) == expected["svc_discovery"]
            assert update_bkmonitor.called
            assert cattr.unstructure(update_bkmonitor.call_args[0][0]) == expected["bk_monitor"]


class TestSMartDescriptionHandler:
    @pytest.fixture
    def app_desc(self, one_px_png) -> Dict:
        return {
            'author': 'blueking',
            'introduction': 'blueking app',
            'is_use_celery': False,
            'version': '0.0.1',
            'env': [],
            "logo_b64data": one_px_png,
        }

    def test_app_creation(self, random_name, bk_user, app_desc, one_px_png):
        app_desc.update(
            {
                'app_code': random_name,
                'app_name': random_name,
            }
        )
        SMartDescriptionHandler(app_desc).handle_app(bk_user)
        application = Application.objects.get(code=random_name)
        assert application is not None
        # 由于 ProcessedImageField 会将 logo 扩展为 144,144, 因此这里判断对应的位置的标记位
        logo_content = application.logo.read()
        assert logo_content[19] == 144
        assert logo_content[23] == 144

    def test_app_update_existed(self, bk_app, bk_user, app_desc):
        app_desc.update(
            {
                'app_code': bk_app.code,
                'app_name': bk_app.name,
                'desktop': {'width': 303, 'height': 100},
            }
        )
        SMartDescriptionHandler(app_desc).handle_app(bk_user)
        product = Product.objects.get(code=bk_app.code)
        assert product.displayoptions.width == 303

    def test_deployment_normal(self, random_name, bk_deployment, app_desc):
        app_desc.update(
            {
                'app_code': random_name,
                'app_name': random_name,
                'env': [{'key': 'BKAPP_FOO', 'value': '1'}],
            }
        )
        SMartDescriptionHandler(app_desc).handle_deployment(bk_deployment)

        desc_obj = DeploymentDescription.objects.get(deployment=bk_deployment)
        assert EnvVariablesReader(desc_obj).read_as_dict() == {'BKAPP_FOO': '1'}

    @pytest.mark.parametrize(
        "memory, expected_plan_name",
        [
            (512, "Starter"),
            (1024, "Starter"),
            (1536, "4C2G5R"),
            (2048, "4C2G5R"),
            (3072, "4C4G5R"),
            (4096, "4C4G5R"),
            (8192, "4C4G5R"),
        ],
    )
    def test_bind_process_spec_plans(self, random_name, bk_deployment, app_desc, memory, expected_plan_name):
        app_desc.update(
            {
                'app_code': random_name,
                'app_name': random_name,
                'env': [{'key': 'BKAPP_FOO', 'value': '1'}],
                'container': {'memory': memory},
            }
        )
        SMartDescriptionHandler(app_desc).handle_deployment(bk_deployment)

        desc_obj = DeploymentDescription.objects.get(deployment=bk_deployment)
        assert desc_obj.runtime["processes"]["web"]["plan"] == expected_plan_name

    @pytest.mark.parametrize(
        "is_use_celery, expected_services",
        [
            (True, [ServiceSpec(name="mysql"), ServiceSpec(name="rabbitmq")]),
            (False, [ServiceSpec(name="mysql")]),
        ],
    )
    def test_app_data_to_desc(self, random_name, app_desc, is_use_celery, expected_services):
        app_desc.update({'app_code': random_name, 'app_name': random_name, "is_use_celery": is_use_celery})
        assert SMartDescriptionHandler(app_desc).app_desc.default_module.services == expected_services

    @pytest.mark.parametrize(
        'libraries, expected', [([], []), ([dict(name='foo', version='bar')], [dict(name='foo', version='bar')])]
    )
    def test_libraries(self, random_name, app_desc, libraries, expected):
        app_desc.update({'app_code': random_name, 'app_name': random_name, "libraries": libraries})
        plugin = SMartDescriptionHandler(app_desc).app_desc.get_plugin(AppDescPluginType.APP_LIBRARIES)
        assert plugin
        assert plugin["data"] == expected


@pytest.fixture()
def app_data(request, random_name):
    if request.param == AppSpecVersion.VER_1:
        return {
            'author': 'blueking',
            'introduction': 'blueking app',
            'is_use_celery': False,
            'version': '0.0.1',
            'env': [],
            'language': 'python',
            'app_code': random_name,
            'app_name': random_name,
        }
    return {
        'spec_version': AppSpecVersion.VER_2,
        'app_version': '0.0.1',
        'app': {'bk_app_code': random_name, 'bk_app_name': random_name},
        'modules': {'default': {'is_default': True, 'language': 'python'}},
    }


@pytest.mark.parametrize("app_data", [(AppSpecVersion.VER_1), (AppSpecVersion.VER_2)], indirect=True)
def test_app_data_to_desc(app_data, random_name):
    desc = get_desc_handler(app_data).app_desc
    assert desc.name_zh_cn == random_name
    assert desc.code == random_name
    plugin = desc.get_plugin(AppDescPluginType.APP_VERSION)
    assert plugin
    assert plugin['data'] == '0.0.1'
    assert desc.default_module.language == AppLanguage.PYTHON
