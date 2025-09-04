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

import logging
from typing import TYPE_CHECKING, List

from django.db import transaction

from paasng.misc.tools.smart_app.constants import SmartBuildPhaseType
from paasng.misc.tools.smart_app.exceptions import NoUnlinkedSmartBuildPhaseError
from paasng.misc.tools.smart_app.models import SmartBuildPhase

from .steps import SmartBuildStepManager

if TYPE_CHECKING:
    from paasng.misc.tools.smart_app.models import SmartBuildRecord

logger = logging.getLogger(__name__)


class SmartBuildPhaseManager:
    """Common manager for SmartBuildPhase model"""

    def __init__(self, smart_build: "SmartBuildRecord"):
        self.smart_build = smart_build

    def list_phase_types(self) -> List[SmartBuildPhaseType]:
        """List All SmartBuildPhaseType"""

        return [SmartBuildPhaseType.PREPARATION, SmartBuildPhaseType.BUILD]

    @transaction.atomic
    def get_or_create(self, phase_type: SmartBuildPhaseType) -> SmartBuildPhaseType:
        """Get or Create SmartBuildPhase Object"""
        try:
            return self._get_existing_phase(phase_type)
        except NoUnlinkedSmartBuildPhaseError:
            # Create new phase
            smart_build_phase = SmartBuildPhase.objects.create(
                type=phase_type.value, smart_build=self.smart_build, tenant_id=self.smart_build.tenant_id
            )

            SmartBuildStepManager.create_step_instances(smart_build_phase, phase_type)

            return smart_build_phase

    def _get_existing_phase(self, phase_type: SmartBuildPhaseType) -> SmartBuildPhase:
        """[private] Get existing SmartBuildPhase, raise NoUnlinkedSmartBuildPhaseError if not exists"""
        try:
            return self.smart_build.phases.get(type=phase_type.value)
        except SmartBuildPhase.DoesNotExist:
            raise NoUnlinkedSmartBuildPhaseError(f"No existing phase: {phase_type}")
