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
"""Handlers triggered by Django signals(events)"""
import logging

from django.dispatch import receiver

from paasng.engine.models import Deployment
from paasng.engine.signals import pre_appenv_deploy
from paasng.platform.applications.models import Application
from paasng.platform.applications.signals import post_create_application

from .apigw import safe_sync_apigw
from .models import BkPluginProfile, is_bk_plugin

logger = logging.getLogger(__name__)


@receiver(post_create_application)
def on_plugin_app_created(sender, application: Application, **kwargs):
    """Do extra jobs after a plugin was created"""
    if not is_bk_plugin(application):
        logger.debug('Initializing plugin: "%s" is not plugin type, will not proceed.', application)
        return

    BkPluginProfile.objects.get_or_create_by_application(application)  # Create profile object


@receiver(pre_appenv_deploy)
def on_pre_deployment(sender, deployment: Deployment, **kwargs):
    """Sync plugin's API-Gateway resource when application was deployed"""
    application = deployment.app_environment.module.application
    if not is_bk_plugin(application):
        logger.debug('Syncing plugin\'s api-gw resource: "%s" is not plugin type, will not proceed.', application)
        return

    if not application.bk_plugin_profile.is_synced:
        logger.info('Syncing api-gw resource for %s, triggered by deployment.', application)
        safe_sync_apigw(application)
