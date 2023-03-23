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
from typing import TYPE_CHECKING

from paasng.engine.models.steps import StepMetaSet
from paasng.platform.modules.helpers import ModuleRuntimeManager

if TYPE_CHECKING:
    from paasng.engine.models import EngineApp


class DeployStepPicker:
    """部署步骤选择器"""

    @classmethod
    def pick(cls, engine_app: 'EngineApp') -> StepMetaSet:
        """通过 engine_app 选择部署阶段应该绑定的步骤"""
        m = ModuleRuntimeManager(engine_app.env.module)
        # 以 SlugBuilder 匹配为主, 不存在绑定直接走缺省步骤集
        builder = m.get_slug_builder(raise_exception=False)
        if builder is None:
            return cls._get_default_meta_set()

        meta_sets = StepMetaSet.objects.filter(metas__builder_provider=builder).order_by("-created").distinct()
        if not meta_sets:
            return cls._get_default_meta_set()

        # NOTE: 目前一个 builder 只会关联一个 StepMetaSet
        return meta_sets[0]

    @classmethod
    def _get_default_meta_set(self):
        """防止由于后台配置缺失而影响部署流程, 绑定默认的 StepMetaSet"""
        try:
            best_matched_set = StepMetaSet.objects.get(is_default=True)
        except StepMetaSet.DoesNotExist:
            best_matched_set = StepMetaSet.objects.all().latest('-created')
        except StepMetaSet.MultipleObjectsReturned:
            best_matched_set = StepMetaSet.objects.filter(is_default=True).order_by("-created")[0]
        return best_matched_set
