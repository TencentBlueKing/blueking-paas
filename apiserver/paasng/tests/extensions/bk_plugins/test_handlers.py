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
from unittest.mock import patch

import pytest

from paasng.extensions.bk_plugins.handlers import on_pre_deployment
from tests.engine.setup_utils import create_fake_deployment

pytestmark = pytest.mark.django_db


@patch('paasng.extensions.bk_plugins.handlers.safe_sync_apigw')
def test_on_pre_deployment(safe_sync_apigw, bk_plugin_app):
    deployment = create_fake_deployment(bk_plugin_app.default_module)
    on_pre_deployment(None, deployment=deployment)
    assert safe_sync_apigw.called is True
