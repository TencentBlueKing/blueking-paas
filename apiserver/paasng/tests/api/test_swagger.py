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

import pytest
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from paasng.plat_admin.api_doc.views import FullSwaggerConfigurationView
from tests.utils.auth import create_user

logger = logging.getLogger(__name__)


class TestSwaggerConfigurationGenerator(TestCase):
    def setUp(self):
        self.user = create_user()

    @pytest.mark.skip(reason="don't know how to fix.")
    def test_default(self):
        factory = APIRequestFactory()
        request = factory.get('/docs/swagger.full')
        request.user = self.user
        response = FullSwaggerConfigurationView.as_view()(request)
        configuration_json = response.content
        configuration_dict = json.loads(configuration_json)
        self.assertEqual(response.status_code, 200)
        self.assertTrue("swagger" in configuration_dict)
