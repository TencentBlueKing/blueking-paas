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

import atexit
from pathlib import Path

import cattr
from django.conf import settings
from django.utils.crypto import get_random_string
from filelock import FileLock

from paas_wl.infras.cluster.constants import ClusterFeatureFlag, ClusterType
from paas_wl.infras.cluster.models import APIServer, Cluster, IngressConfig


def _generate_cluster_name() -> str:
    """Generate a random cluster name for testing. This function use a file lock to ensure
    the cluster name is identical across different test processes.
    """
    file_path = Path(__file__).parent / ".random"

    def _cleanup():
        file_path.unlink(missing_ok=True)

    # Remove the file on exit
    atexit.register(_cleanup)

    with FileLock(str(file_path.absolute()) + ".lock"):
        if file_path.is_file():
            return file_path.read_text().strip()

        _name = get_random_string(6)
        file_path.write_text(_name)
        return _name


CLUSTER_NAME_FOR_TESTING = _generate_cluster_name()


def build_default_cluster():
    """Build a default cluster using configurations in the settings."""
    cluster = Cluster(
        name=CLUSTER_NAME_FOR_TESTING,
        region=settings.DEFAULT_REGION_NAME,
        is_default=True,
        ingress_config=cattr.structure(
            {
                "app_root_domains": [{"name": "example.com"}],
                "sub_path_domains": [{"name": "example.com"}],
                "default_ingress_domain_tmpl": "%s.unittest.com",
                "frontend_ingress_ip": "0.0.0.0",
                "port_map": {"http": "80", "https": "443"},
            },
            IngressConfig,
        ),
        annotations={
            "bcs_cluster_id": "",
            "bcs_project_id": "",
            "bk_biz_id": "",
        },
        ca_data=settings.FOR_TESTS_CLUSTER_CONFIG["ca_data"],
        cert_data=settings.FOR_TESTS_CLUSTER_CONFIG["cert_data"],
        key_data=settings.FOR_TESTS_CLUSTER_CONFIG["key_data"],
        token_value=settings.FOR_TESTS_CLUSTER_CONFIG["token_value"],
        feature_flags=ClusterFeatureFlag.get_default_flags_by_cluster_type(ClusterType.NORMAL),
    )
    apiserver = APIServer(
        host=settings.FOR_TESTS_CLUSTER_CONFIG["url"],
        cluster=cluster,
        overridden_hostname=settings.FOR_TESTS_CLUSTER_CONFIG["force_domain"],
    )
    return cluster, apiserver
