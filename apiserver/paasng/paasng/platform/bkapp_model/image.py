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
from typing import List

from paas_wl.bk_app.cnative.specs.credentials import split_image
from paas_wl.workloads.images.entities import ImageCredentialRef
from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.modules.models import BuildConfig
from paasng.platform.modules.models.module import Module

logger = logging.getLogger(__name__)


def get_image_credential_refs(module: Module) -> List[ImageCredentialRef]:
    """获取有效的用户自定义镜像凭证 reference"""
    refs = []

    try:
        build_config = BuildConfig.objects.get(module=module)
        if build_config.image_credential_name and build_config.image_repository:
            refs.append(
                ImageCredentialRef(
                    credential_name=build_config.image_credential_name,
                    image=split_image(build_config.image_repository),
                )
            )
    except Exception:
        pass

    if refs:
        return refs

    # TODO v1alph1 版本迁移完成后, 删除下面的代码并重构当前函数
    for proc_spec in ModuleProcessSpec.objects.filter(module=module):
        if proc_spec.image and proc_spec.image_credential_name:
            refs.append(
                ImageCredentialRef(credential_name=proc_spec.image_credential_name, image=split_image(proc_spec.image))
            )

    return refs
