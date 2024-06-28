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

import pytest
from django.utils.translation import override
from rest_framework.exceptions import ValidationError

from paasng.platform.smart_app.services.app_desc import get_app_description
from paasng.platform.sourcectl.models import SPStat
from paasng.utils.i18n import gettext_lazy

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("meta_info", "is_valid", "name_in_desc"),
    [
        ({}, False, None),
        ({"app_name": "阿尔法"}, False, None),
        (
            {
                "app_name": "阿尔法",
                "app_name_en": "alpha",
                "app_code": "foo",
                "author": "blueking",
                "introduction": "blueking app",
                "is_use_celery": False,
                "version": "0.0.1",
                "env": [],
            },
            True,
            gettext_lazy({"zh-cn": "阿尔法", "en": "alpha"}),
        ),
    ],
)
def test_get_app_description(meta_info, is_valid, name_in_desc):
    stat = SPStat(name="name", version="v1", size=1, meta_info=meta_info, sha256_signature="signature")
    if not is_valid:
        with pytest.raises(ValidationError):
            get_app_description(stat)
        return

    app_desc = get_app_description(stat)
    with override("zh-cn"):
        assert app_desc.name_zh_cn == name_in_desc
    with override("en"):
        assert app_desc.name_en == name_in_desc
