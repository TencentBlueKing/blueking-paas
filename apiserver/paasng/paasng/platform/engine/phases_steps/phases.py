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
import logging
from typing import TYPE_CHECKING, List

from django.db import transaction

from paasng.platform.engine.constants import RuntimeType
from paasng.platform.engine.exceptions import NoUnlinkedDeployPhaseError, StepNotInPresetListError
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.engine.models.phases import DeployPhase, DeployPhaseTypes
from paasng.platform.engine.phases_steps.steps import DeployStepPicker
from paasng.platform.modules.specs import ModuleSpecs

if TYPE_CHECKING:
    from paasng.platform.applications.models import ModuleEnvironment

logger = logging.getLogger(__name__)


class DeployPhaseManager:
    """Common manager for DeployPhase model"""

    def __init__(self, env: "ModuleEnvironment"):
        self.env = env

    def list_phase_types(self) -> List[DeployPhaseTypes]:
        """List All DeployPhaseTypes supported by this ModuleEnvironment"""
        specs = ModuleSpecs(self.env.module)
        if specs.runtime_type == RuntimeType.CUSTOM_IMAGE:
            return [DeployPhaseTypes.PREPARATION, DeployPhaseTypes.RELEASE]
        return [DeployPhaseTypes.PREPARATION, DeployPhaseTypes.BUILD, DeployPhaseTypes.RELEASE]

    def get_or_create_all(self) -> List[DeployPhase]:
        """Get or Create All DeployPhase Object supported by this ModuleEnvironment"""
        return [self._get_or_create(phase_type) for phase_type in self.list_phase_types()]

    @transaction.atomic
    def attach(self, phase_type: DeployPhaseTypes, deployment: Deployment) -> DeployPhase:
        """关联当前 Deployment 和已经创建好的 EngineApp"""
        target_phase = self._get_unattached_phase(phase_type)
        target_phase.attach(deployment)
        return target_phase

    @transaction.atomic
    def rebuild_step_if_outdated(self, phase: DeployPhase) -> bool:
        """
        如果已绑定的部署与当前 pick 出来的步骤有出入，重建所有部署步骤
        :param phase: 部署阶段对象
        :return: 返回是否已重建
        """
        picked_step_set = DeployStepPicker.pick(self.env.engine_app)
        logger.debug("choosing step set<%s>...", picked_step_set.name)

        existing_names = list(phase.steps.all().values_list("name", flat=True))
        if set(existing_names) == set(picked_step_set.list_sorted_step_names(DeployPhaseTypes(phase.type))):
            # 修复存量数据可能存在的异常
            _try_bind_meta_to_step_of_phase(phase)
            return False

        phase.steps.all().delete()
        picked_step_set.create_step_instances(phase)
        return True

    @transaction.atomic
    def _get_or_create(self, phase_type: DeployPhaseTypes) -> DeployPhase:
        """[private] 创建或获取一个未绑定 Deployment 的可部署阶段对象，如果存在未绑定的则直接返回"""
        try:
            return self._get_unattached_phase(phase_type)
        except NoUnlinkedDeployPhaseError:
            deploy_phase = DeployPhase.objects.create(type=phase_type.value, engine_app=self.env.engine_app)
            try:
                # pick 是一个一次性的操作，当 pick 出匹配的 step meta set 之后，
                # 将 Phase 和 step 关联，step meta set 也就没有其他用处了
                step_set = DeployStepPicker.pick(self.env.engine_app)
                step_set.create_step_instances(deploy_phase)
            except Exception:
                logger.exception("failed to pick step set")

            return deploy_phase

    def _get_unattached_phase(self, phase_type: DeployPhaseTypes) -> DeployPhase:
        """[private] 获取一个未绑定 Deployment 的可部署阶段对象, 如果不存在则抛异常 NoUnlinkedDeployPhaseError"""
        # TODO: 给 DeployPhase 添加组合的唯一索引, 避免重复创建 DeployPhase
        qs = DeployPhase.objects.filter(type=phase_type.value, engine_app=self.env.engine_app, deployment=None)
        try:
            return qs.get()
        except DeployPhase.MultipleObjectsReturned:
            return qs.first()
        except DeployPhase.DoesNotExist:
            raise NoUnlinkedDeployPhaseError("no unattached phases available")


def _try_bind_meta_to_step_of_phase(phase: DeployPhase):
    # 存在存量步骤实例并未绑定元信息，会影响步骤探测，尝试绑定
    for s in phase.steps.filter(meta__isnull=True):
        try:
            s.try_to_bind_meta()
        except StepNotInPresetListError as e:
            logger.warning("%s: step of deployment in page may stay empty", e.message)
            continue
