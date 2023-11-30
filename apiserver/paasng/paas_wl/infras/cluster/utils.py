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
from paas_wl.bk_app.applications.models import WlApp
from paas_wl.infras.cluster.models import Cluster


def get_default_cluster_by_region(region: str) -> Cluster:
    """Get default cluster name by region"""
    try:
        return Cluster.objects.get(is_default=True, region=region)
    except Cluster.DoesNotExist:
        raise RuntimeError(f"No default cluster found in region `{region}`")


def get_cluster_by_app(app: WlApp) -> Cluster:
    """Get kubernetes cluster by given app

    :param app: WlApp object
    :raise RuntimeError: App has an invalid cluster_name defined
    """
    cluster_name = app.config_set.latest().cluster
    if not cluster_name:
        return get_default_cluster_by_region(app.region)

    try:
        return Cluster.objects.get(name=cluster_name)
    except Cluster.DoesNotExist:
        raise RuntimeError(f"Can not find a cluster called {cluster_name}")
