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
from bkpaas_auth.core.constants import ProviderType
from bkpaas_auth.core.encoder import user_id_encoder
from django.db import models

from paasng.utils.models import BkUserField


class TestBkUserField:
    def test_set(self):
        class M(models.Model):
            creator = BkUserField()

            class Meta:
                app_label = "foo"

        foo_u = user_id_encoder.encode(ProviderType.BK, "foo")
        instance = M(creator=foo_u)
        assert instance.creator.username == "foo"

        bar_u = user_id_encoder.encode(ProviderType.BK, "bar")
        instance.creator = bar_u
        assert instance.creator.username == "bar"
