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
import pytest

from paasng.extensions.declarative.handlers import get_desc_handler
from paasng.extensions.declarative.protections import modifications_not_allowed
from paasng.platform.applications.models import Application
from paasng.platform.core.protections.exceptions import ConditionNotMatched

pytestmark = pytest.mark.django_db


class TestModificationsNotAllowed:
    def test_normal_app(self, bk_app):
        modifications_not_allowed(bk_app)

    def test_desc_app(self, random_name, bk_user):
        get_desc_handler(
            dict(
                spec_version=2,
                app=dict(bk_app_code=random_name, bk_app_name=random_name),
                modules={random_name: {"is_default": True, "language": "python"}},
            )
        ).handle_app(bk_user)
        app = Application.objects.get(code=random_name)
        with pytest.raises(ConditionNotMatched):
            assert modifications_not_allowed(app)
