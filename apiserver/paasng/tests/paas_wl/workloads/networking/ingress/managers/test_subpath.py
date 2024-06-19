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

import pytest

from paas_wl.infras.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.workloads.networking.ingress.managers.subpath import SubPathAppIngressMgr, assign_subpaths
from paas_wl.workloads.networking.ingress.models import AppSubpath
from tests.utils.mocks.cluster import cluster_ingress_config

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


class TestSubPathAppIngressMgr:
    def test_list_desired_domains_configured(self, bk_stag_wl_app):
        AppSubpath.objects.create_obj(bk_stag_wl_app, "/foo/")
        AppSubpath.objects.create_obj(bk_stag_wl_app, "/bar/")

        ingress_mgr = SubPathAppIngressMgr(bk_stag_wl_app)
        with cluster_ingress_config({"sub_path_domains": [{"name": "main.example.com"}]}):
            domains = ingress_mgr.list_desired_domains()
            assert len(domains) == 1
            assert domains[0].host == "main.example.com"
            assert domains[0].path_prefix_list == ["/foo/", "/bar/"]

    def test_list_desired_domains_not_configured(self, bk_stag_wl_app):
        ingress_mgr = SubPathAppIngressMgr(bk_stag_wl_app)
        with cluster_ingress_config({"sub_path_domains": []}):
            domains = ingress_mgr.list_desired_domains()
            assert len(domains) == 0


@pytest.mark.auto_create_ns()
class TestAssignSubpaths:
    @pytest.fixture(autouse=True)
    def _configure(self):
        with cluster_ingress_config({"sub_path_domains": [{"name": "main.example.com"}]}):
            yield

    def test_brand_new_paths(self, bk_stag_wl_app):
        paths = ["/foo/", "/bar/"]
        assign_subpaths(bk_stag_wl_app, paths, "foo-service")

        ingress_mgr = SubPathAppIngressMgr(bk_stag_wl_app)
        ingress = ingress_mgr.get()

        assert len(ingress.domains) == 1
        assert ingress.domains[0].path_prefix_list == ["/foo/", "/bar/"]

    def test_subpath_transfer_partally(self, bk_stag_wl_app, bk_prod_wl_app):
        paths = ["/foo/", "/bar/"]
        assign_subpaths(bk_stag_wl_app, paths, "foo-service")

        ingress = SubPathAppIngressMgr(bk_stag_wl_app).get()
        assert len(ingress.domains) == 1
        assert ingress.domains[0].path_prefix_list == ["/foo/", "/bar/"]

        # Transfer "/bar/" to bk_prod_wl_app
        paths_app2 = ["/bar/", "/foobar/"]
        assign_subpaths(bk_prod_wl_app, paths_app2, "foo-service")

        ingress = SubPathAppIngressMgr(bk_stag_wl_app).get()
        assert len(ingress.domains) == 1
        assert ingress.domains[0].path_prefix_list == ["/foo/"]

        ingress = SubPathAppIngressMgr(bk_prod_wl_app).get()
        assert len(ingress.domains) == 1
        assert ingress.domains[0].path_prefix_list == ["/bar/", "/foobar/"]

    def test_subpath_transfer_fully(self, bk_stag_wl_app, bk_prod_wl_app):
        paths = ["/foo/"]
        assign_subpaths(bk_stag_wl_app, paths, "foo-service")

        assert SubPathAppIngressMgr(bk_stag_wl_app).get().domains[0].path_prefix_list == ["/foo/"]
        with pytest.raises(AppEntityNotFound):
            SubPathAppIngressMgr(bk_prod_wl_app).get()

        # Transfer all paths to bk_prod_wl_app
        assign_subpaths(bk_prod_wl_app, paths, "foo-service")
        with pytest.raises(AppEntityNotFound):
            SubPathAppIngressMgr(bk_stag_wl_app).get()
        ingress = SubPathAppIngressMgr(bk_prod_wl_app).get()
        assert len(ingress.domains) == 1
        assert ingress.domains[0].path_prefix_list == paths
