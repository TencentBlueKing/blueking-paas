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
from typing import Any, Dict, List, Optional

from paas_wl.bk_app.cnative.specs.constants import IMAGE_CREDENTIALS_REF_ANNO_KEY, ResQuotaPlan
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppProcess
from paasng.platform.bkapp_model.importer.entities import CommonImportResult
from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)


def import_processes(module: Module, processes: List[BkAppProcess], annotations: Dict) -> CommonImportResult:
    """Import processes data.

    :param processes: A list of BkAppProcess items.
    :return: The import result object.
    """
    ret = CommonImportResult()

    # Build the index of existing data first to remove data later.
    # Data structure: {process name: pk}
    existing_index = {}
    for proc_spec in ModuleProcessSpec.objects.filter(module=module):
        existing_index[proc_spec.name] = proc_spec.pk

    # Update or create data
    for process in processes:
        defaults: Dict[str, Any] = {
            "command": process.command,
            "args": process.args,
            "port": process.targetPort,
            "target_replicas": process.replicas,
            "plan_name": process.resQuotaPlan or ResQuotaPlan.P_DEFAULT,
        }
        if autoscaling := process.autoscaling:
            defaults["autoscaling"] = True
            defaults["scaling_config"] = {
                "min_replicas": autoscaling.minReplicas,
                "max_replicas": autoscaling.maxReplicas,
                "policy": autoscaling.policy,
            }

        # 兼容使用 v1alpha1 支持多镜像的场景
        if process.image:
            defaults["image"] = process.image
        if process.imagePullPolicy:
            defaults["image_pull_policy"] = process.imagePullPolicy
        if image_credential_name := _extract_image_credential_name(process.name, annotations):
            defaults["image_credential_name"] = image_credential_name

        _, created = ModuleProcessSpec.objects.update_or_create(module=module, name=process.name, defaults=defaults)
        ret.incr_by_created_flag(created)
        # Move out from the index
        existing_index.pop(process.name, None)

    # Remove existing data that is not touched.
    ret.deleted_num, _ = ModuleProcessSpec.objects.filter(module=module, id__in=existing_index.values()).delete()
    return ret


def _extract_image_credential_name(process_name: str, annotations: Dict) -> Optional[str]:
    """extract image credential name from annotations(v1alpha1).

    v1alpha1:
        bkapp.paas.bk.tencent.com/image-credentials: true
        bkapp.paas.bk.tencent.com/image-credentials.web: xxx # image credential name

    v1alpha2:
        bkapp.paas.bk.tencent.com/image-credentials: xxx--dockerconfigjson # image pull secret name
    """
    value = annotations.get(IMAGE_CREDENTIALS_REF_ANNO_KEY)
    if not value:
        return None

    if value == "true":
        return annotations.get(f"{IMAGE_CREDENTIALS_REF_ANNO_KEY}.{process_name}")

    return None
