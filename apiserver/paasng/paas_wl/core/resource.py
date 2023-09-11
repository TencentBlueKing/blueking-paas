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
# Utils related with app resources
from typing import Union

from paas_wl.platform.applications.models import WlApp
from paas_wl.platform.applications.models.managers.app_metadata import get_metadata
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.modules.constants import ModuleName
from paasng.platform.modules.models import Module


class CNativeBkAppNameGenerator:
    """Resource name generator for cnative applications"""

    @classmethod
    def generate(cls, obj: Union[Module, WlApp, ModuleEnvironment]) -> str:
        """Generate name of the BkApp resource by env.

        :param obj: Union[Module, WlApp, ModuleEnvironment] object
        :return: BkApp resource name
        """
        if isinstance(obj, Module):
            module_name = obj.name
            code = obj.application.code
        elif isinstance(obj, ModuleEnvironment):
            module_name = obj.module.name
            code = obj.application.code
        else:
            mdata = get_metadata(obj)
            module_name = mdata.module_name
            code = mdata.get_paas_app_code()
        return cls.make_name(app_code=code, module_name=module_name)

    @classmethod
    def make_name(cls, app_code: str, module_name: str) -> str:
        # 兼容考虑，如果模块名为 default 则不在 BkApp 名字中插入 module 名
        if module_name == ModuleName.DEFAULT.value:
            name = app_code
        else:
            name = f'{app_code}-m-{module_name}'
        return name.replace("_", "0us0")
