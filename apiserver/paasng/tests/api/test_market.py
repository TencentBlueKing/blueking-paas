# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import json
import logging
import uuid

import pytest
from django.conf import settings
from rest_framework.reverse import reverse

from paasng.publish.market.constant import OpenMode
from paasng.publish.market.models import DisplayOptions, Product, Tag
from tests.utils.helpers import create_app

pytestmark = pytest.mark.django_db

logger = logging.getLogger(__name__)


@pytest.fixture
def existed_app(bk_app):
    """Create a existed app to test conflicted situations"""
    return create_app()


@pytest.fixture
def tag(bk_app):
    """A tag fixture for testing"""
    parent = Tag.objects.create(name="parent test", region=bk_app.region)
    return Tag.objects.create(name="test", region=bk_app.region, parent=parent)


@pytest.fixture
def creation_params(bk_app, tag):
    return {
        'application': bk_app.code,
        'tag': tag.pk,
        'introduction': 'test',
        'description': 'A test application',
        'type': 1,
        'resizable': True,
        'is_win_maximize': True,
        'win_bars': True,
        'height': 600,
        'width': 800,
        'detail': 'test',
        'contact': 'nobody',
        'related_corp_products': [],
    }


class TestCreateMarketApp:
    def test_name_conflicted_with_existed_app(self, existed_app, api_client, creation_params):
        creation_params.update({'name': existed_app.name})
        response = api_client.post(reverse('api.market.products.list'), data=creation_params, format='json')
        assert response.status_code == 400
        assert 'name_en' in response.json()['fields_detail']
        assert 'name_zh_cn' in response.json()['fields_detail']

    def test_duplicated_creation(self, bk_app, api_client, creation_params):
        creation_params.update({'name': bk_app.name})
        response = api_client.post(reverse('api.market.products.list'), data=creation_params, format='json')
        assert response.status_code == 201

        # Make a duplicated creation
        dup_response = api_client.post(reverse('api.market.products.list'), data=creation_params, format='json')
        assert dup_response.status_code == 400
        assert 'application' in dup_response.json()['fields_detail']

    def test_normal(self, bk_app, api_client, creation_params):
        creation_params.update({'name': bk_app.name, 'width': 803})

        response = api_client.post(reverse('api.market.products.list'), data=creation_params, format='json')
        assert 'application' in response.json()
        assert response.status_code == 201

        assert Product.objects.get(code=bk_app.code).name == bk_app.name
        assert DisplayOptions.objects.get(product__code=bk_app.code).width == 803
        # If the opening method is not specified, the default is to open in the desktop
        assert DisplayOptions.objects.get(product__code=bk_app.code).open_mode == OpenMode.NEW_TAB.value


class TestGetAndUpdateProduct:
    @pytest.fixture(autouse=True)
    def existed_product(self, api_client, bk_app, creation_params):
        """Create product beforehand"""
        creation_params.update({'name': bk_app.name})
        api_client.post(reverse('api.market.products.list'), data=creation_params, format='json')

    def test_get_market_app(self, bk_app, api_client):
        response = api_client.get(reverse('api.market.products.detail', args=(bk_app.code,)), format='json')
        assert response.status_code == 200
        assert response.json()['name'] == bk_app.name
        assert response.json()['open_mode'] == OpenMode.NEW_TAB.value

    def test_update_market_app(self, api_client, bk_app):
        # Get the origin product value
        response = api_client.get(reverse('api.market.products.detail', args=(bk_app.code,)), format='json')
        data = response.json()

        # Change name to a new value
        target_name = uuid.uuid4().hex[:20]
        data["name"] = target_name
        data["width"] = 841
        data['contact'] = 'nobody;nobody1'
        data['open_mode'] = OpenMode.NEW_TAB.value
        # 可见范围
        data['visiable_labels'] = [
            {"id": 100, "type": "department", "name": "xx部门"},
            {"id": 2001, "type": "user", "name": "user1"},
        ]
        put_response = api_client.put(
            reverse('api.market.products.detail', args=(bk_app.code,)), data=data, format='json'
        )
        assert put_response.status_code == 200
        product = Product.objects.get(code=bk_app.code)
        assert product.name == target_name
        assert product.displayoptions.width == 841
        assert product.displayoptions.contact == 'nobody;nobody1'
        assert product.displayoptions.open_mode == OpenMode.NEW_TAB.value
        # 开启了应用市场配置，则测试数据同步
        if getattr(settings, "BK_CONSOLE_DBCONF", None):
            from paasng.platform.core.storages.sqlalchemy import console_db
            from paasng.publish.sync_market.managers import AppManger

            session = console_db.get_scoped_session()
            console_app = AppManger(session).get(bk_app.code)
            assert console_app.width == product.displayoptions.width == 841
            assert console_app.open_mode == product.displayoptions.open_mode
            try:
                assert json.loads(console_app.extra)['contact'] == product.displayoptions.contact
            except AttributeError:
                logger.info('The extra attribute of the application does not exist, skip verification')
            try:
                assert console_app.visiable_labels == product.transform_visiable_labels()
            except AttributeError:
                logger.info('The visiable_labels attribute of the application does not exist, skip verification')
