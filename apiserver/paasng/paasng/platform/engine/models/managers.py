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

import logging
from textwrap import dedent
from typing import TYPE_CHECKING, List, Optional, Type

import yaml
from django.db import transaction
from django.db.models import Model
from django.forms.models import model_to_dict
from pydantic import BaseModel

from paasng.platform.engine.constants import JobStatus
from paasng.platform.engine.models import ConfigVar
from paasng.platform.engine.models.config_var import CONFIG_VAR_INPUT_FIELDS, ENVIRONMENT_ID_FOR_GLOBAL
from paasng.platform.engine.models.deployment import Deployment
from paasng.platform.engine.models.offline import OfflineOperation

if TYPE_CHECKING:
    from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)


class DeployOperationManager:
    """目前用来统一管理 Deployment & Offline 两类的操作，旨在替换掉 Operation Model"""

    def __init__(self, module: "Module"):
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


class ApplyResult(BaseModel):
    create_num: int = 0
    overwrited_num: int = 0
    ignore_num: int = 0
    deleted_num: int = 0


class PlainConfigVar(BaseModel):
    key: str
    value: str
    description: str
    environment_name: str


class ExportedConfigVars(BaseModel):
    env_variables: List[PlainConfigVar]

    def to_file_content(self, extra_cmt: str = "") -> str:
        """Dump the ExportedConfigVars to file content(yaml format)

        :param str extra_cmt: Additional comments will be appended after the file header description
        :returns: A yaml string, containing ConfigVar and description comments
        """
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
        if extra_cmt:
            directions += extra_cmt.rstrip() + "\n"

        content = yaml.safe_dump(self.dict(), allow_unicode=True, default_flow_style=False)
        return f"{directions}{content}"

    @classmethod
    def from_list(cls, config_vars: List[ConfigVar]) -> "ExportedConfigVars":
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
    def apply_vars_to_module(self, module: "Module", config_vars: List[ConfigVar]) -> ApplyResult:
        """Apply a list of `config_vars` objects to the `module`, these objects may
        be created or will overwrite the old ones with the same name.

        :returns: A result object that describes the details.
        """
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

    @transaction.atomic
    def remove_bulk(self, module: "Module", exclude_keys: List[str]) -> int:
        """Remove a bulk of config vars.

        :param exclude_keys: The keys to exclude from removing.
        :returns: The number of removed objects.
        """
        ret = 0
        for obj in module.configvar_set.all():
            if obj.key not in exclude_keys:
                obj.delete()
                ret += 1
        return ret

    def clone_vars(self, source: "Module", dest: "Module") -> ApplyResult:
        """Clone All Config Vars from `source` Module  to `dest` Module, but ignore all built-in ones."""
        return self.apply_vars_to_module(dest, list(source.configvar_set.filter(is_builtin=False)))

    @transaction.atomic
    def batch_save(self, module: "Module", config_vars: List[ConfigVar]) -> ApplyResult:
        """Save environment variables in batches, including adding, updating, and deleting"""
        instance_list = module.configvar_set.filter(is_builtin=False).prefetch_related("environment")
        instance_mapping = {obj.id: obj for obj in instance_list}

        # validate: new ConfigVar must have value
        errors = []
        for var_data in config_vars:
            if (not var_data.id or var_data.id not in instance_mapping) and not var_data.value:
                errors.append({"key": var_data.key, "error": "value is required"})
        if errors:
            raise ValueError(errors)

        # Create new instance if id is not provided
        create_list = [item for item in config_vars if not item.id]

        # Perform updates and remove ids from instance_mapping.
        update_config_vars = {item.id: item for item in config_vars if item.id}
        overwrited_num = 0
        for var_id, var_data in update_config_vars.items():
            obj = instance_mapping.get(var_id)
            # If the id is provided, but if the id is not in the db, need to create a new data
            if obj is None:
                var_data.id = None
                create_list.append(var_data)
            else:
                instance_mapping.pop(var_id)
                # If the value is not provided, use the existing value
                if not var_data.value:
                    var_data.value = obj.value
                # If it is inconsistent with existing data, it needs to be updated
                if not obj.is_equivalent_to(var_data):
                    _update_data_dict = model_to_dict(var_data, fields=CONFIG_VAR_INPUT_FIELDS)
                    ConfigVar.objects.filter(id=var_id).update(**_update_data_dict)
                    overwrited_num += 1

        # Perform deletions.
        deleted_num = len(instance_mapping)
        for obj in instance_mapping.values():
            obj.delete()

        ConfigVar.objects.bulk_create(create_list)

        return ApplyResult(
            create_num=len(create_list),
            overwrited_num=overwrited_num,
            deleted_num=deleted_num,
        )
