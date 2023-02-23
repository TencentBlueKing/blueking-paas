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
from unittest import mock

import pytest
from django_dynamic_fixture import G

from paasng.engine.constants import JobStatus
from paasng.publish.market.models import Product
from paasng.publish.market.protections import AppPublishPreparer
from tests.engine.setup_utils import create_fake_deployment

pytestmark = pytest.mark.django_db


def test_create_default_product(bk_app):
    product = Product.objects.create_default_product(bk_app)
    assert product == bk_app.get_product()


@pytest.fixture(autouse=True)
def _setup_deployed_statuses():
    """Set up the deployed statuses of the application, use false result by default."""
    with mock.patch('paasng.publish.market.protections.env_is_deployed', return_value=False):
        yield


@pytest.fixture
def with_all_deployed():
    """Make sure the application has completed deployment in all environments."""
    with mock.patch('paasng.publish.market.protections.env_is_deployed', return_value=True):
        yield


class TestAppPublishPreparer:
    """TestCases for AppPublishPreparer"""

    app_extra_fields = {'source_init_template': 'dj18_with_auth'}

    def test_fresh_app(self, bk_app):
        preparer = AppPublishPreparer(bk_app)
        status = preparer.perform()
        action_names = [item.action_name for item in status.failed_conditions]

        assert status.activated
        assert 'fill_product_info' in action_names
        assert 'deploy_prod_env' in action_names

    def test_app_with_product(self, bk_app):
        _ = G(Product, application=bk_app)
        preparer = AppPublishPreparer(bk_app)
        status = preparer.perform()
        action_names = [item.action_name for item in status.failed_conditions]

        assert status.activated
        assert 'fill_product_info' not in action_names
        assert 'deploy_prod_env' in action_names

    def test_app_with_product_prod_env(self, bk_app, bk_module, with_all_deployed):
        _ = G(Product, application=bk_app)
        deployment = create_fake_deployment(bk_module)
        deployment.status = JobStatus.SUCCESSFUL.value
        deployment.save()

        preparer = AppPublishPreparer(bk_app)
        status = preparer.perform()
        assert not status.activated
