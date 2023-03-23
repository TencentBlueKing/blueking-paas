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
import logging
from textwrap import dedent
from typing import TYPE_CHECKING, List, Optional, Type

import yaml
from django.db import transaction
from django.db.models import Model
from pydantic import BaseModel

from paasng.engine.constants import JobStatus, RuntimeType
from paasng.engine.exceptions import NoUnlinkedDeployPhaseError, StepNotInPresetListError
from paasng.engine.models import ConfigVar
from paasng.engine.models.config_var import ENVIRONMENT_ID_FOR_GLOBAL
from paasng.engine.models.deployment import Deployment
from paasng.engine.models.offline import OfflineOperation
from paasng.engine.models.phases import DeployPhase, DeployPhaseTypes
from paasng.engine.phases_steps.display_blocks import get_display_blocks_by_type
from paasng.engine.phases_steps.picker import DeployStepPicker
from paasng.platform.modules.specs import ModuleSpecs

if TYPE_CHECKING:
    from paasng.platform.applications.models import ModuleEnvironment
    from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)


class DeployOperationManager:
    """目前用来统一管理 Deployment & Offline 两类的操作，旨在替换掉 Operation Model"""

    def __init__(self, module: 'Module'):
        self.module = module
        self.model_classes: List[Type[Model]] = [Deployment, OfflineOperation]

    def has_pending(self, environment: Optional[str] = None) -> bool:
        """是否存在正在进行的操作"""
        envs = self.module.envs.all()
        if environment:
            envs = [
                envs.get(environment=environment),
            ]

        for model_class in self.model_classes:
            # 需要保证 pending 状态的准确性
            if model_class.objects.filter(app_environment__in=envs, status=JobStatus.PENDING.value).exists():
                # 两种操作任意存在一种 pending 状态都直接返回
                return True

        return False


class DeployPhaseManager:
    def __init__(self, env: 'ModuleEnvironment'):
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

        existing_names = list(phase.steps.all().values_list('name', flat=True))
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


class DeployDisplayBlockRenderer:
    @staticmethod
    def get_display_blocks_info(phase_obj: DeployPhase) -> dict:
        """获取该阶段的静态展示信息"""
        # Q: 为什么这里不直接存渲染后的内容？
        # A: 因为很多信息是没有办法在应用创建拿到的，如果要存这些信息，那么需要引入信息及时同步的复杂度
        # 所以每次请求 deploy skeleton 时，都需要实时渲染一次
        info = dict()
        for b in get_display_blocks_by_type(DeployPhaseTypes(phase_obj.type)):
            info.update(b.get_detail(engine_app=phase_obj.engine_app))
        return info


class ApplyResult(BaseModel):
    create_num: int = 0
    overwrited_num: int = 0
    ignore_num: int = 0


class PlainConfigVar(BaseModel):
    key: str
    value: str
    description: str
    environment_name: str


class ExportedConfigVars(BaseModel):
    env_variables: List[PlainConfigVar]

    def to_file_content(self) -> str:
        """Dump the ExportedConfigVars to file content(yaml format)"""
        directions = dedent(
            """\
            # 环境变量文件字段说明：
            #   - key: 变量名称，仅支持大写字母、数字、下划线
            #   - value: 变量值
            #   - description: 描述文字
            #   - environment_name: 生效环境
            #     - 可选值:
            #       - stag: 预发布环境
            #       - prod: 生产环境
            #       - _global_: 所有环境
            """
        )
        content = yaml.safe_dump(self.dict(), allow_unicode=True, default_flow_style=False)
        return f"{directions}{content}"

    @classmethod
    def from_list(cls, config_vars: List[ConfigVar]) -> 'ExportedConfigVars':
        """serialize provided config vars to an ExportedConfigVars

        :param List[ConfigVar] config_vars: The config_vars set
        :returns: ExportedConfigVars
        """
        instance = ExportedConfigVars(env_variables=[])
        for config_var in config_vars:
            instance.env_variables.append(
                PlainConfigVar(
                    key=config_var.key,
                    value=config_var.value,
                    description=config_var.description or "",
                    environment_name=config_var.environment_name,
                )
            )
        return instance


class ConfigVarManager:
    @transaction.atomic
    def apply_vars_to_module(self, module: 'Module', config_vars: List[ConfigVar]) -> ApplyResult:
        """Apply those `config_vars` to the `module`"""
        create_list = []
        overwrited_list = []

        for var in config_vars:
            existed_obj: Optional[ConfigVar] = None
            try:
                if var.environment_id == ENVIRONMENT_ID_FOR_GLOBAL:
                    existed_obj = module.configvar_set.get(key=var.key, environment_id=ENVIRONMENT_ID_FOR_GLOBAL)
                else:
                    existed_obj = module.configvar_set.get(
                        key=var.key, environment__environment=var.environment.environment
                    )
            except ConfigVar.DoesNotExist:
                logger.debug("Can't find existed config var.")

            if existed_obj is None:
                create_list.append(var.clone_to(module))
            elif not existed_obj.is_equivalent_to(var):
                existed_obj.value, existed_obj.description = var.value, var.description
                overwrited_list.append(existed_obj)

        ConfigVar.objects.bulk_create(create_list)
        for overwrite in overwrited_list:
            overwrite.save()

        return ApplyResult(
            create_num=len(create_list),
            overwrited_num=len(overwrited_list),
            ignore_num=len(config_vars) - len(create_list) - len(overwrited_list),
        )

    def clone_vars(self, source: 'Module', dest: 'Module') -> ApplyResult:
        """Clone All Config Vars from `source` Module  to `dest` Module, but ignore all built-in ones."""
        return self.apply_vars_to_module(dest, list(source.configvar_set.filter(is_builtin=False)))
