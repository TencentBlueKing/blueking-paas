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
import time
import typing
from typing import Any, Dict, Iterable, Text

from vendor.command import InstancesBasedCommand
from vendor.models import UserPolicy

if typing.TYPE_CHECKING:
    from vendor.client import Client


class Command(InstancesBasedCommand):
    help = "Sync user policy to rabbitmq cluster"

    def add_arguments(self, parser):
        parser.add_argument("-t", "--tags", type=int, nargs="+", help="policy tag")
        parser.add_argument("-p", "--policies", type=int, nargs="+", help="policy id")
        parser.add_argument("-s", "--sleep", type=int, default=0, help="sleep seconds before starting next action")
        parser.add_argument("-A", "--add", action="store_true", default=False, help="allow to add enabled policy")
        parser.add_argument(
            "-U", "--update", action="store_true", default=False, help="allow to update enabled policy"
        )
        parser.add_argument(
            "-D", "--delete", action="store_true", default=False, help="allow to delete disabled policy"
        )
        parser.add_argument("--dry-run", action="store_true", default=False, help="dry run")

        super().add_arguments(parser)

    def get_policies(self, cluster, policies, tags, *args, **kwargs) -> Iterable[UserPolicy]:
        """Get policies filtered by args"""
        qs = UserPolicy.objects.all()
        if cluster:
            qs = qs.filter(cluster_id=cluster)

        if policies:
            qs = qs.filter(pk__in=policies)

        return qs

    def patch_policies(
        self, virtual_host: Text, client: 'Client', names: Iterable[Text], policies: Dict[Text, UserPolicy]
    ):
        """Update policies, add a new policy if no exists, otherwise update it"""
        for i in names:
            params = policies[i].dict()
            client.user_policy.create(
                virtual_host,
                params["name"],
                params,
            )

    def delete_policies(self, virtual_host: Text, client: 'Client', names: Iterable[Text]):
        """Delete policies in the rabbitmq cluster"""
        for i in names:
            client.user_policy.delete(virtual_host, i)

    def compare_policies(self, a: Dict[Text, Any], b: Dict[Text, Any]):
        """Compare policies a and b if is equal"""
        for k, v in a.items():
            if k not in b:
                return False
            if b[k] != v:
                return False

        return True

    def handle(self, add, update, delete, dry_run, sleep, *args, **kwargs):
        vhosts = self.get_vhost_set(*args, **kwargs)
        enabled_policies = {}
        disabled_policies = {}

        for p in self.get_policies(*args, **kwargs):
            if p.enable:
                enabled_policies[p.name] = p
            else:
                disabled_policies[p.name] = p

        client = self.get_client_by_cluster(*args, **kwargs)
        for vhost in vhosts:
            time.sleep(sleep)
            # policies which defined in the rabbitmq cluster
            policies = {p["name"]: p for p in client.user_policy.get(vhost)}

            if add:
                names = enabled_policies.keys() - policies.keys()
                print(f"policies will be add: {names}")
                if not dry_run:
                    self.patch_policies(vhost, client, names, enabled_policies)

            if update:
                names = []
                for n in enabled_policies.keys() & policies.keys():
                    if not self.compare_policies(enabled_policies[n].dict(), policies[n]):
                        names.append(n)
                print(f"policies will be update: {names}")
                if not dry_run:
                    self.patch_policies(vhost, client, names, enabled_policies)

            if delete:
                names = disabled_policies & policies.keys()
                print(f"policies will be delete: {names}")
                if not dry_run:
                    self.delete_policies(vhost, client, names)
