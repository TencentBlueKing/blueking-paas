# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import logging
import os
from pathlib import Path
from typing import Dict, List

import jinja2
import requests
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import status

from paasng.monitoring.monitor.alert_rules.config import RuleConfig

from .exceptions import AsCodeAPIError

logger = logging.getLogger(__name__)


class AsCodeClient:
    """AsCodeClient 用于向 bkmonitor 下发告警规则

    :param app_code: 应用 code
    :param rule_configs: app 的告警规则配置. 结合 MonitorAsCode 模板, 渲染出 bkmonitor 理解的告警规则
    :param default_receivers: app 的默认告警接收者
    """

    def __init__(self, app_code: str, rule_configs: List[RuleConfig], default_receivers: List[str]):
        self.app_code = app_code
        self.rule_configs = rule_configs
        self.default_receivers = default_receivers
        self.default_notice_group_name = f"[{self.app_code}] {_('通知组')}"

    def apply_rule_configs(self):
        """下发告警规则"""
        self._validate()
        configs = self._render_configs()
        self._apply_rule_configs(configs)

    def _validate(self):
        for config in self.rule_configs:
            if config.app_code != self.app_code:
                raise ValueError(
                    f'apply rules error: app_code({config.app_code}) from rule_configs not match '
                    f'app_code({self.app_code})'
                )

    def _render_configs(self) -> Dict:
        """按照 MonitorAsCode 规则, 渲染出如下示例目录结构:

        ├── notice
          └── notice.yaml
        └── rule
          ├── high_cpu_usage.yaml
          └── high_mem_usage.yaml
        """
        tpl_dir = Path(os.path.dirname(__file__))
        loader = jinja2.FileSystemLoader([tpl_dir / 'rules_tpl', tpl_dir / 'notice_tpl'])
        j2_env = jinja2.Environment(loader=loader, trim_blocks=True)

        configs = {}
        for conf in self.rule_configs:
            ctx = conf.to_dict()

            if set(conf.receivers) == set(self.default_receivers):
                ctx['notice_group_name'] = self.default_notice_group_name
            else:
                # 配置中告警接收者与 app 的默认告警接收者不一致时, 单独创建告警组
                ctx['notice_group_name'] = f"{conf.alert_rule_display_name} {_('通知组')}"
                configs[f'notice/{conf.alert_rule_name}.yaml'] = j2_env.get_template('notice.yaml.j2').render(
                    **{'notice_group_name': ctx['notice_group_name'], 'receivers': conf.receivers}
                )

            configs[f'rule/{conf.alert_rule_name}.yaml'] = j2_env.get_template(f'{conf.alert_code}.yaml.j2').render(
                **ctx
            )

        # 配置 App 默认通知组
        configs['notice/default_notice.yaml'] = j2_env.get_template('notice.yaml.j2').render(
            **{'notice_group_name': self.default_notice_group_name, 'receivers': self.default_receivers}
        )

        return configs

    def _apply_rule_configs(self, configs: Dict):
        """同步告警配置到 bkmonitor"""
        resp = requests.post(
            url=f'{settings.BK_MONITORV3_URL}/rest/v2/as_code/import_config/',
            json={
                'bk_biz_id': settings.MONITOR_AS_CODE_CONF.get('bk_biz_id'),
                'app': self.app_code,
                'configs': configs,
                'overwrite': False,
            },
            headers={'Authorization': f"Bearer {settings.MONITOR_AS_CODE_CONF.get('token')}"},
            verify=False,
        )

        err_msg_format = f'ascode import alert rule configs of app_code({self.app_code}) error: {{err_msg}}'

        if resp.status_code == status.HTTP_200_OK:
            resp_data = resp.json()
            if resp_data['result']:
                return

            logger.error(err_msg_format.format(err_msg=resp.text))
            raise AsCodeAPIError(resp_data['message'])

        logger.error(err_msg_format.format(err_msg=resp.text))
        raise AsCodeAPIError('unknown error')
