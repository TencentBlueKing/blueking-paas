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

"""Sync instance configs with remote services"""

import logging
from typing import Optional

from django.core.management.base import BaseCommand

from paasng.accessories.servicehub.exceptions import ServiceObjNotFound
from paasng.accessories.servicehub.models import RemoteServiceEngineAppAttachment
from paasng.accessories.servicehub.remote import RemoteServiceMgr
from paasng.accessories.servicehub.remote.manager import RemoteEngineAppInstanceRel, RemoteServiceObj
from paasng.accessories.servicehub.remote.store import get_remote_store

logger = logging.getLogger("commands")


class Command(BaseCommand):
    help = "Sync instance configs with remote services"

    def add_arguments(self, parser):
        parser.add_argument(
            "--name",
            required=True,
            type=str,
            help=("specify a remote service name"),
            choices=[service["name"] for service in get_remote_store().all()],
        )

    def _get_service(self, mgr: RemoteServiceMgr, name: str) -> Optional[RemoteServiceObj]:
        """Iterate all regions to get remote service object"""
        try:
            return mgr.find_by_name(name)
        except ServiceObjNotFound:
            return None

    def handle(self, *args, **options):
        store = get_remote_store()
        mgr = RemoteServiceMgr(store)
        service_name = options["name"]

        svc = self._get_service(mgr, service_name)
        if not svc:
            logger.error(f'Service named "{service_name}" not found, abort.')
            return

        if not svc.supports_inst_config():
            logger.error(f"Service {svc.name} does not supports feature: instance config, abort.")
            return

        attachments = RemoteServiceEngineAppAttachment.objects.filter(service_id=svc.uuid)
        for rel_obj in attachments:
            if not rel_obj.service_instance_id:
                logger.debug("Ignore not provisioned instances")
                continue

            rel = RemoteEngineAppInstanceRel(rel_obj, mgr, store)
            rel.sync_instance_config()
            logger.info(f"Synced instance {rel_obj.service_instance_id}")
