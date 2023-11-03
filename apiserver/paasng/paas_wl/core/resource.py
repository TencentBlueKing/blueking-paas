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
from typing import Dict, Union

from paas_wl.bk_app.applications.constants import WlAppType
from paas_wl.bk_app.applications.models import Release, WlApp
from paas_wl.bk_app.applications.models.managers.app_metadata import get_metadata
from paas_wl.bk_app.cnative.specs.constants import MODULE_NAME_ANNO_KEY
from paas_wl.bk_app.processes.constants import PROCESS_NAME_KEY
from paas_wl.infras.resources.generation.mapper import MapperProcConfig
from paas_wl.infras.resources.generation.version import AppResVerManager
from paas_wl.utils.command import get_command_name
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


def get_process_selector(app: 'WlApp', process_type: str) -> Dict[str, str]:
    """Return labels selector dict by process type, useful for construct Deployment body
    and related Service. To get a result, the app must has been released successfully and
    the process_type must exists.

    NOTE: Modify this function carefully as it might disrupt the process of updating
    the related deployment resources.

    :param app: The app object.
    :param process_type: The type of process, such as "web"
    """
    if app.type == WlAppType.CLOUD_NATIVE:
        return {MODULE_NAME_ANNO_KEY: app.module_name, PROCESS_NAME_KEY: process_type}

    # Use the info of the latest release object
    release = Release.objects.get_latest(app)
    command_name = get_command_name(release.get_procfile()[process_type])
    proc_config = MapperProcConfig(
        app=app,
        type=process_type,
        version=release.version,
        command_name=command_name,
    )
    return {"pod_selector": AppResVerManager(app).curr_version.deployment(proc_config).pod_selector}
