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
from typing import Any, Dict, List

from paas_wl.bk_app.cnative.specs.constants import ResQuotaPlan
from paas_wl.bk_app.cnative.specs.crd.bk_app import BkAppProcess, Probe
from paasng.platform.bkapp_model.importer.entities import CommonImportResult
from paasng.platform.bkapp_model.models import ModuleProcessSpec
from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)


def to_snake_case_probe(probe: Probe) -> Dict[str, Any]:
    """将探针字段转换成下划线格式"""
    exec_handler, http_get_handler, tcp_socket_handler = None, None, None
    if probe.exec:
        exec_handler = {"command": probe.exec.command}
    elif probe.httpGet:
        http_get_handler = {
            "path": probe.httpGet.path,
            "port": probe.httpGet.port,
            "http_headers": [{"name": h.name, "value": h.value} for h in probe.httpGet.httpHeaders],
            "host": probe.httpGet.host,
            "scheme": probe.httpGet.scheme,
        }
    elif probe.tcpSocket:
        tcp_socket_handler = {"port": probe.tcpSocket.port, "host": probe.tcpSocket.host}

    return {
        "exec": exec_handler,
        "http_get": http_get_handler,
        "tcp_socket": tcp_socket_handler,
        "initial_delay_seconds": probe.initialDelaySeconds,
        "timeout_seconds": probe.timeoutSeconds,
        "period_seconds": probe.periodSeconds,
        "success_threshold": probe.successThreshold,
        "failure_threshold": probe.failureThreshold,
    }


def import_processes(module: Module, processes: List[BkAppProcess]) -> CommonImportResult:
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
            # 为了兼容普通应用从 app_desc v2 升级到 app_desc v3, 导入时需要清空 proc_command 字段
            "proc_command": None,
        }
        if autoscaling := process.autoscaling:
            defaults["autoscaling"] = True
            defaults["scaling_config"] = {
                "min_replicas": autoscaling.minReplicas,
                "max_replicas": autoscaling.maxReplicas,
                "policy": autoscaling.policy,
            }
        if probes := process.probes:
            defaults["probes"] = {
                "liveness": to_snake_case_probe(probes.liveness) if probes.liveness else None,
                "readiness": to_snake_case_probe(probes.readiness) if probes.readiness else None,
                "startup": to_snake_case_probe(probes.startup) if probes.startup else None,
            }

        _, created = ModuleProcessSpec.objects.update_or_create(module=module, name=process.name, defaults=defaults)
        ret.incr_by_created_flag(created)
        # Move out from the index
        existing_index.pop(process.name, None)

    # Remove existing data that is not touched.
    ret.deleted_num, _ = ModuleProcessSpec.objects.filter(module=module, id__in=existing_index.values()).delete()
    return ret
