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
from typing import Any, Dict, Set

from django.core.management.base import CommandParser
from paas_service.base_vendor import get_provider_cls
from paas_service.models import ServiceInstance
from vendor.command import InstancesBasedCommand
from vendor.helper import InstanceHelper
from vendor.models import Cluster

logger = logging.getLogger(__name__)


class Command(InstancesBasedCommand):
    help = "Evict connection in federation cluster"

    def add_arguments(self, parser: 'CommandParser'):
        super().add_arguments(parser)
        parser.add_argument("-f", "--force", action="store_true", default=False)
        parser.add_argument("--dry-run", action="store_true", default=False)
        parser.add_argument("--on-error-resume", default=False, action="store_true", help="on error resume")

    def recovery_instance(
        self,
        vhosts: "Set[str]",
        cluster: "Cluster",
        instance: "ServiceInstance",
        force: "bool",
        dry_run: "bool",
    ):
        helper = InstanceHelper(instance)
        if helper.get_cluster_id() != cluster.pk:
            return

        credentials = helper.get_credentials()
        if vhosts and credentials.vhost not in vhosts:
            return

        bill = helper.get_bill()
        if bill.action != "delete" and not force:
            return

        provider_cls = get_provider_cls()
        provider = provider_cls()

        print(
            f"recovery instance {instance}, vhost: {credentials.vhost},",
            f"bill action: {bill.action}, deleted: {instance.to_be_deleted}",
        )
        if dry_run:
            return

        with bill.log_context() as context:  # type: Dict[str, Any]
            provider.create_instance(context.get("engine_app_name", bill.name), bill, context, cluster)
            bill.action = "create"

        if instance.to_be_deleted:
            instance.to_be_deleted = False
            instance.save(update_fields="to_be_deleted")

    def handle(self, vhost, force, on_error_resume, dry_run, *args, **kwargs):
        instances = self.get_instances(*args, **kwargs) or ServiceInstance.objects.all()
        vhosts = set(vhost)
        cluster = self.get_cluster(*args, **kwargs)

        for i in instances:
            try:
                self.recovery_instance(vhosts=vhosts, force=force, cluster=cluster, instance=i, dry_run=dry_run)
            except Exception as e:
                print(f"handle instance {i} error, {e}")
