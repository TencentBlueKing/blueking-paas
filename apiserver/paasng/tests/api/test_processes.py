# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

from unittest import mock

import pytest

from paas_wl.bk_app.processes.controllers import ProcessesInfo
from paasng.platform.applications.constants import DeployPolicy

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


@pytest.mark.usefixtures("_with_wl_apps")
def test_list_processes_for_isolated_ai_agent(api_client, bk_cnative_app, bk_stag_env):
    bk_cnative_app.is_ai_agent_app = True
    bk_cnative_app.deploy_policy = DeployPolicy.ISOLATED.value
    bk_cnative_app.save(update_fields=["is_ai_agent_app", "deploy_policy"])
    processes_info = ProcessesInfo(processes=[], rv_proc="100", rv_inst="100")

    with (
        mock.patch(
            "paas_wl.bk_app.processes.views.list_cnative_module_processes_specs",
            return_value={"default": []},
        ),
        mock.patch(
            "paas_wl.bk_app.processes.views.ProcInstByEnvListWatcher.list_instances_only",
            return_value=processes_info,
        ) as mocked_list_instances,
        mock.patch("paas_wl.bk_app.processes.views.ProcInstByEnvListWatcher.list") as mocked_list_deployments,
        mock.patch(
            "paas_wl.bk_app.processes.views.get_builtin_addr_preferred",
            return_value=(False, None),
        ),
        mock.patch(
            "paas_wl.bk_app.processes.views.get_env_deployed_version_info",
            return_value=("buildpack", None),
        ),
        mock.patch(
            "paas_wl.bk_app.processes.views.CNativeListAndWatchProcsViewSet.get_repo_url",
            return_value=None,
        ),
    ):
        response = api_client.get(f"/api/bkapps/applications/{bk_cnative_app.code}/envs/stag/processes/list/")

    assert response.status_code == 200
    assert response.data["rv_proc"] == "100"
    assert response.data["rv_inst"] == "100"
    assert response.data["data"][0]["module_name"] == bk_stag_env.module.name
    mocked_list_instances.assert_called_once_with()
    mocked_list_deployments.assert_not_called()
