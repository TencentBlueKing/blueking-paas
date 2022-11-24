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
from vendor.client import Client
from vendor.command import FederationBaseCommand
from vendor.models import Cluster


class Command(FederationBaseCommand):
    def delete_upstream(self, cluster: Cluster, upstream: Cluster, name, vhost):
        cluster_client = Client.from_cluster(cluster)

        cluster_client.user_policy.delete(vhost, name)

        cluster_client.federation.delete_upstream(name, vhost)

        upstream_client = Client.from_cluster(upstream)
        username = self.get_username(cluster, upstream, name, vhost)
        upstream_client.user.delete(username)

    def handle(self, upstream_cluster, vhost, exclude_vhost, name, on_error_resume, *args, **kwargs):
        cluster = self.get_cluster(*args, **kwargs)
        upstream = self.get_cluster(cluster=upstream_cluster)
        vhosts = self.get_available_vhosts(cluster, upstream, vhost, exclude_vhost)

        for i in vhosts:
            print(f"handling vhost: {i}")
            try:
                self.delete_upstream(
                    cluster=cluster,
                    upstream=upstream,
                    name=name,
                    vhost=i,
                )
            except Exception as err:
                if not on_error_resume:
                    raise

                print(err)
