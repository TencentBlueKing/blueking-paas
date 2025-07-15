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

from pathlib import Path
from typing import Dict
from unittest import mock

import pytest
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from paasng.accessories.smart_advisor.advisor import DocumentaryLinkAdvisor
from paasng.accessories.smart_advisor.tags import get_dynamic_tag
from paasng.misc.monitoring.monitor.alert_rules.ascode.client import AsCodeClient
from paasng.misc.monitoring.monitor.alert_rules.config.constants import DEFAULT_RULE_CONFIGS
from paasng.misc.monitoring.monitor.alert_rules.config.entities import AlertCode
from paasng.misc.monitoring.monitor.models import AppAlertRule
from paasng.utils import safe_jinja2
from tests.utils.basic import generate_random_string

random_vhost = generate_random_string()
random_cluster_id = generate_random_string()


@pytest.fixture(autouse=True)
def mock_import_configs():
    with mock.patch.object(AsCodeClient, "_apply_rule_configs", return_value=None) as mock_method:
        yield mock_method


@pytest.fixture(scope="module", autouse=True)
def _mock_metric_label():
    with mock.patch.dict(
        "paasng.misc.monitoring.monitor.alert_rules.config.metric_label.LABEL_VALUE_QUERY_FUNCS",
        {
            "vhost": lambda app_code, run_env, module_name: random_vhost,
            "bcs_cluster_id": lambda app_code, run_env, module_name: random_cluster_id,
        },
    ):
        yield


@pytest.fixture()
def wl_namespaces(bk_stag_env, bk_prod_env, _with_wl_apps) -> Dict[str, str]:
    return {"prod": bk_prod_env.wl_app.namespace, "stag": bk_stag_env.wl_app.namespace}


@pytest.fixture()
def create_module_for_alert(bk_module_2, _with_wl_apps):
    return bk_module_2


@pytest.fixture()
def bk_app_init_rule_configs(bk_app, wl_namespaces):
    tpl_dir = Path(settings.BASE_DIR) / "paasng" / "misc" / "monitoring" / "monitor" / "alert_rules" / "ascode"
    j2_env = safe_jinja2.FileEnvironment(
        [tpl_dir / "rules_tpl", tpl_dir / "notice_tpl", tpl_dir / "notice_tpl"], trim_blocks=True
    )

    app_code = bk_app.code
    rule_configs = DEFAULT_RULE_CONFIGS
    notice_group_name = f"{_('应用成员')}"

    default_rules = {
        AlertCode.HIGH_CPU_USAGE.value: {
            "alert_rule_name_format": f"{app_code}-default-{{env}}-high_cpu_usage",
            "template_name": "high_cpu_usage.yaml.j2",
        },
        AlertCode.HIGH_MEM_USAGE.value: {
            "alert_rule_name_format": f"{app_code}-default-{{env}}-high_mem_usage",
            "template_name": "high_mem_usage.yaml.j2",
        },
        AlertCode.POD_RESTART.value: {
            "alert_rule_name_format": f"{app_code}-default-{{env}}-pod_restart",
            "template_name": "pod_restart.yaml.j2",
        },
        AlertCode.OOM_KILLED.value: {
            "alert_rule_name_format": f"{app_code}-default-{{env}}-oom_killed",
            "template_name": "oom_killed.yaml.j2",
        },
    }

    if settings.RABBITMQ_MONITOR_CONF.get("enabled", False):
        default_rules[AlertCode.HIGH_RABBITMQ_QUEUE_MESSAGES.value] = {
            "alert_rule_name_format": f"{app_code}-default-{{env}}-high_rabbitmq_queue_messages",
            "template_name": "high_rabbitmq_queue_messages.yaml.j2",
        }

    init_rule_configs = {}
    notice_template = j2_env.get_template("notice_template.yaml.j2")
    for alert_code, c in default_rules.items():
        for env in ["stag", "prod"]:
            doc_url = ""
            tag = get_dynamic_tag(f"saas_monitor:{alert_code}")
            links = DocumentaryLinkAdvisor().search_by_tags([tag], limit=1)
            if links:
                doc_url = f"。处理建议: {links[0].location}"
            notice_template_content = notice_template.render(doc_url=doc_url)

            alert_rule_name = c["alert_rule_name_format"].format(env=env)
            init_rule_configs[f"rule/{alert_rule_name}.yaml"] = j2_env.get_template(c["template_name"]).render(
                alert_rule_display_name=f"{rule_configs[alert_code]['display_name']} [default:{env}]",
                app_code=app_code,
                run_env=env,
                alert_code=alert_code,
                enabled=True,
                metric_labels={
                    "namespace": wl_namespaces[env],
                    "vhost": random_vhost,
                    "bcs_cluster_id": random_cluster_id,
                },
                threshold_expr=rule_configs[alert_code]["threshold_expr"],
                notice_group_name=notice_group_name,
                notice_template=notice_template_content,
            )

    notice_group_config = {
        "notice/default_notice.yaml": j2_env.get_template("notice.yaml.j2").render(
            notice_group_name=f"{_('应用成员')}", receivers=bk_app.get_developers()
        )
    }

    return init_rule_configs, notice_group_config


@pytest.fixture()
def cpu_usage_alert_rule_obj(bk_app):
    return AppAlertRule.objects.create(
        alert_code=AlertCode.HIGH_CPU_USAGE.value,
        display_name="high_cpu_usage",
        enabled=True,
        threshold_expr="N/A",
        receivers=bk_app.get_developers(),
        application=bk_app,
        environment="stag",
        module=bk_app.get_default_module(),
        tenant_id=bk_app.tenant_id,
    )
