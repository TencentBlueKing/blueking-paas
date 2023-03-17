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
"""Patch existed Kubernetes service object, make it compatible with new services/manager interface
"""
import logging

from django.core.management.base import BaseCommand

from paas_wl.platform.applications.models import WlApp
from paas_wl.resources.base.exceptions import ResourceMissing
from paas_wl.resources.base.kres import KService
from paas_wl.resources.utils.basic import get_client_by_app

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """This command patches existed kubernetes services:

    - Update annotation field: add "process_type"
    """

    help = 'Patch existed kubernetes services'

    def handle(self, *args, **options):
        for app in WlApp.objects.all().order_by('created'):
            client = get_client_by_app(app)
            for process_type in app.get_structure():
                default_service_name = f"{app.region}-{app.scheduler_safe_name}-{process_type}"
                try:
                    svc = KService(client).get(default_service_name, namespace=app.namespace)
                except ResourceMissing:
                    continue

                print(f"Existed service found for app {app.name}, serivce={default_service_name}")
                annotations = svc.metadata.annotations or {}
                if not annotations:
                    print(f"Updating service, set annotation to process_type={process_type}")
                    annotations['process_type'] = process_type
                    svc.metadata.annotations = annotations
                    KService(client).replace_or_patch(default_service_name, svc, namespace=app.namespace)
