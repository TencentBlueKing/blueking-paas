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
from django.dispatch import receiver

from paasng.engine.models.deployment import Deployment
from paasng.engine.signals import post_appenv_deploy
from paasng.platform.applications.models import ApplicationEnvironment
from paasng.platform.applications.signals import application_member_updated

from . import tasks


@receiver(post_appenv_deploy)
def create_rules_after_deploy(sender: ApplicationEnvironment, deployment: Deployment, **kwargs):
    if not deployment.has_succeeded():
        return

    tasks.create_rules.delay(sender.application.code, sender.module.name, sender.environment)


@receiver(application_member_updated)
def update_notice_group(sender, application, **kwargs):
    tasks.update_notice_group.delay(application.code)
