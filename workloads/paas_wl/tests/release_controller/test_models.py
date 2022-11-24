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
import pytest

from paas_wl.platform.applications.models.build import BuildProcess
from paas_wl.utils.constants import BuildStatus

pytestmark = pytest.mark.django_db


class TestInterruptionAllowed:
    def test_default(self, bp: BuildProcess):
        assert bp.check_interruption_allowed() is False

    def test_set_true(self, bp: BuildProcess):
        bp.set_logs_was_ready()
        assert bp.check_interruption_allowed() is True

    def test_finished_status(self, bp: BuildProcess):
        bp.status = BuildStatus.SUCCESSFUL
        bp.save(update_fields=['status'])
        bp.set_logs_was_ready()
        assert bp.check_interruption_allowed() is False
