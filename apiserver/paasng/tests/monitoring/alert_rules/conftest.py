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
from pathlib import Path
from unittest import mock

import jinja2
import pytest
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from paasng.monitoring.monitor.alert_rules.ascode.client import AsCodeClient
from paasng.monitoring.monitor.alert_rules.constants import DEFAULT_RULE_CONFIGS
from paasng.monitoring.monitor.models import AppAlertRule


@pytest.fixture(scope="module", autouse=True)
def mock_import_configs():
    with mock.patch.object(AsCodeClient, "_apply_rule_configs", return_value=None) as mock_method:
        yield mock_method


@pytest.fixture
def bk_app_init_rule_configs(bk_app):

    tpl_dir = Path(settings.BASE_DIR) / 'paasng' / 'monitoring' / 'monitor' / 'alert_rules' / 'ascode'
    loader = jinja2.FileSystemLoader([tpl_dir / 'rules_tpl', tpl_dir / 'notice_tpl'])
    j2_env = jinja2.Environment(loader=loader, trim_blocks=True)

    app_code = bk_app.code
    app_scoped_configs = DEFAULT_RULE_CONFIGS['app_scoped']
    module_scoped_configs = DEFAULT_RULE_CONFIGS['module_scoped']
    notice_group_name = f"[{app_code}] {_('通知组')}"

    return {
        f'rule/{app_code}_stag_page_50x.yaml': j2_env.get_template('page_50x.yaml.j2').render(
            alert_rule_display_name=f"[{app_code}:stag] {app_scoped_configs['page_50x']['display_name']}",
            enabled=True,
            threshold_expr=app_scoped_configs['page_50x']['threshold_expr'],
            notice_group_name=notice_group_name,
        ),
        f'rule/{app_code}_prod_page_50x.yaml': j2_env.get_template('page_50x.yaml.j2').render(
            alert_rule_display_name=f"[{app_code}:prod] {app_scoped_configs['page_50x']['display_name']}",
            enabled=True,
            threshold_expr=app_scoped_configs['page_50x']['threshold_expr'],
            notice_group_name=notice_group_name,
        ),
        f'rule/{app_code}_default_stag_high_cpu_usage.yaml': j2_env.get_template('high_cpu_usage.yaml.j2').render(
            alert_rule_display_name=f"[{app_code}:default:stag] "
            f"{module_scoped_configs['high_cpu_usage']['display_name']}",
            enabled=True,
            namespace=f'bkapp-{app_code}-stag',
            threshold_expr=module_scoped_configs['high_cpu_usage']['threshold_expr'],
            notice_group_name=notice_group_name,
        ),
        f'rule/{app_code}_default_prod_high_cpu_usage.yaml': j2_env.get_template('high_cpu_usage.yaml.j2').render(
            alert_rule_display_name=f"[{app_code}:default:prod] "
            f"{module_scoped_configs['high_cpu_usage']['display_name']}",
            enabled=True,
            namespace=f'bkapp-{app_code}-prod',
            threshold_expr=module_scoped_configs['high_cpu_usage']['threshold_expr'],
            notice_group_name=notice_group_name,
        ),
        f'rule/{app_code}_default_stag_high_mem_usage.yaml': j2_env.get_template('high_mem_usage.yaml.j2').render(
            alert_rule_display_name=f"[{app_code}:default:stag] "
            f"{module_scoped_configs['high_mem_usage']['display_name']}",
            enabled=True,
            namespace=f'bkapp-{app_code}-stag',
            threshold_expr=module_scoped_configs['high_mem_usage']['threshold_expr'],
            notice_group_name=notice_group_name,
        ),
        f'rule/{app_code}_default_prod_high_mem_usage.yaml': j2_env.get_template('high_mem_usage.yaml.j2').render(
            alert_rule_display_name=f"[{app_code}:default:prod] "
            f"{module_scoped_configs['high_mem_usage']['display_name']}",
            enabled=True,
            namespace=f'bkapp-{app_code}-prod',
            threshold_expr=module_scoped_configs['high_mem_usage']['threshold_expr'],
            notice_group_name=notice_group_name,
        ),
        'notice/default_notice.yaml': j2_env.get_template('notice.yaml.j2').render(
            notice_group_name=f"[{app_code}] {_('通知组')}", receivers=bk_app.get_developers()
        ),
    }


@pytest.fixture
def cpu_usage_alert_rule_obj(bk_app):
    return AppAlertRule.objects.create(
        alert_code='high_cpu_usage',
        display_name='high_cpu_usage',
        enabled=True,
        threshold_expr='>= 0.8',
        receivers=bk_app.get_developers(),
        application=bk_app,
        environment='stag',
        module=bk_app.get_default_module(),
    )
