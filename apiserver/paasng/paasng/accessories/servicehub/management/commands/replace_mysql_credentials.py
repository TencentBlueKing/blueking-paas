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
import logging
from typing import Optional

from django.core.management.base import BaseCommand

from paasng.accessories.servicehub.exceptions import ServiceObjNotFound
from paasng.accessories.servicehub.models import RemoteServiceEngineAppAttachment
from paasng.accessories.servicehub.remote import RemoteServiceMgr
from paasng.accessories.servicehub.remote.manager import RemotePlainInstanceMgr, RemoteServiceObj
from paasng.accessories.servicehub.remote.store import get_remote_store
from paasng.core.region.models import get_all_regions
from paasng.platform.applications.models import ApplicationEnvironment

logger = logging.getLogger("commands")


class Command(BaseCommand):
    help = (
        "replace mysql credentials with remote services. "
        "This command creates a service_instance object instance "
        "but does not actually allocate resources."
    )

    def add_arguments(self, parser):
        parser.add_argument("--app_code", required=True, type=str, help="application code")
        parser.add_argument("--module_name", required=True, type=str, help="module name")
        parser.add_argument("--env", required=True, type=str, help="environment name")
        parser.add_argument("--mysql_host", required=True, type=str)
        parser.add_argument("--mysql_port", required=True, type=str)
        parser.add_argument("--mysql_username", required=True, type=str)
        parser.add_argument("--mysql_password", required=True, type=str)
        parser.add_argument("--mysql_name", required=True, type=str)
        parser.add_argument("--admin_url", required=False, type=str)
        parser.add_argument("--no-dry-run", dest="dry_run", default=True, action="store_false", help="dry run")

    def _get_service(self, mgr: RemoteServiceMgr, name: str) -> Optional[RemoteServiceObj]:
        """Iterate all regions to get remote service object"""
        for region in get_all_regions():
            try:
                return mgr.find_by_name(name, region)
            except ServiceObjNotFound:
                continue
        return None

    def handle(self, *args, **options):
        store = get_remote_store()
        service_mgr = RemoteServiceMgr(store)

        svc = self._get_service(service_mgr, "mysql")
        if not svc:
            logger.error("Service named gcs_mysql not found, abort.")
            return

        env = ApplicationEnvironment.objects.get(
            application__code=options["app_code"], module__name=options["module_name"], environment=options["env"]
        )
        attachment = RemoteServiceEngineAppAttachment.objects.get(service_id=svc.uuid, engine_app=env.engine_app)
        attachment.service_instance_id = None
        mgr = RemotePlainInstanceMgr(attachment, store)

        credentials = {
            "MYSQL_HOST": options["mysql_host"],
            "MYSQL_PORT": options["mysql_port"],
            "MYSQL_NAME": options["mysql_name"],
            "MYSQL_USER": options["mysql_user"],
            "MYSQL_PASSWORD": options["mysql_password"],
        }
        config = {
            "paas_app_info": {
                "app_id": str(mgr.db_application.id),
                "app_code": str(mgr.db_application.code),
                "app_name": str(mgr.db_application.name),
                "module": mgr.db_module.name,
                "environment": mgr.db_env.environment,
            },
        }
        if options["admin_url"]:
            config["admin_url"] = options["admin_url"]
        if not options["dry_run"]:
            mgr.create(credentials=credentials, config=config)

        self.stdout.write(self.style.NOTICE(f"credentials reset to {credentials}"))
        self.stdout.write(self.style.NOTICE(f"config reset to {config}"))
