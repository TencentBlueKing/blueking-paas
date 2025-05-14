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

"""TestDoubles for paasng.platform.engine module"""

import logging
from contextlib import contextmanager
from typing import Dict, Optional
from unittest import mock

import cattr
import pytest

from paas_wl.bk_app.applications.models.app import WlApp
from paas_wl.infras.cluster.entities import IngressConfig
from paas_wl.infras.cluster.models import Cluster
from paas_wl.infras.cluster.shim import EnvClusterService
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def _cluster_service_allow_nonexisting_wl_apps():
    """Patch the `EnvClusterService` to accept envs which don't have WlApp, this makes the
    testing more convenient because we don't have to create WlApp for each application.
    """
    _orig_method = EnvClusterService.get_cluster_name

    def _get_cluster_name(self):
        try:
            return _orig_method(self)
        except WlApp.DoesNotExist:
            logger.warning("No wl_app found when getting cluster, env: %s", self.env.pk)
            return CLUSTER_NAME_FOR_TESTING

    with mock.patch.object(EnvClusterService, "get_cluster_name", _get_cluster_name):
        yield


@contextmanager
def cluster_ingress_config(config: Optional[Dict] = None, replaced_config: Optional[Dict] = None):
    """Update the cluster ingress config during the context.

    :param config: merge the original config with this value.
    :param replaced_config: replace the original config entirely.
    """
    # Always update the testing cluster by default
    cluster = Cluster.objects.get(name=CLUSTER_NAME_FOR_TESTING)

    new = cattr.unstructure(cluster.ingress_config)
    if config is not None:
        new.update(config)
    elif replaced_config is not None:
        new = replaced_config

    orig_config = cluster.ingress_config
    # Update the config field
    cluster.ingress_config = cattr.structure(new, IngressConfig)
    cluster.save()

    yield

    cluster.ingress_config = orig_config
    cluster.save()
