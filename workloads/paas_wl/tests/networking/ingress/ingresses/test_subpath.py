# -*- coding: utf-8 -*-
import pytest

from paas_wl.networking.ingress.managers.subpath import SubPathAppIngressMgr, assign_subpaths
from paas_wl.networking.ingress.models import AppSubpath
from paas_wl.resources.base.kres import KNamespace
from paas_wl.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.resources.utils.basic import get_client_by_app
from tests.conftest import override_cluster_ingress_attrs
from tests.utils.app import create_app

pytestmark = pytest.mark.django_db


class TestSubPathAppIngressMgr:
    def test_list_desired_domains_configured(self, app):
        AppSubpath.objects.create_obj(app, '/foo/')
        AppSubpath.objects.create_obj(app, '/bar/')

        ingress_mgr = SubPathAppIngressMgr(app)
        with override_cluster_ingress_attrs({'sub_path_domains': [{"name": 'main.example.com'}]}):
            domains = ingress_mgr.list_desired_domains()
            assert len(domains) == 1
            assert domains[0].host == 'main.example.com'
            assert domains[0].path_prefix_list == ['/foo/', '/bar/']

    def test_list_desired_domains_not_configured(self, app):
        ingress_mgr = SubPathAppIngressMgr(app)
        with override_cluster_ingress_attrs({'sub_path_domains': []}):
            domains = ingress_mgr.list_desired_domains()
            assert len(domains) == 0


@pytest.mark.ensure_k8s_namespace
class TestAssignSubpaths:
    @pytest.fixture(autouse=True)
    def configure(self):
        with override_cluster_ingress_attrs({'sub_path_domains': [{"name": 'main.example.com'}]}):
            yield

    def test_brand_new_paths(self, app):
        paths = ['/foo/', '/bar/']
        assign_subpaths(app, paths, 'foo-service')

        ingress_mgr = SubPathAppIngressMgr(app)
        ingress = ingress_mgr.get()

        assert len(ingress.domains) == 1
        assert ingress.domains[0].path_prefix_list == ['/foo/', '/bar/']

    def test_subpath_transfer_partally(self, app):
        paths = ['/foo/', '/bar/']
        assign_subpaths(app, paths, 'foo-service')
        app_2 = create_app()

        # Transfer "/bar/" to app_2
        paths_app2 = ['/bar/', '/foobar/']
        KNamespace(get_client_by_app(app_2)).get_or_create(app_2.namespace)
        assign_subpaths(app_2, paths_app2, 'foo-service')

        ingress = SubPathAppIngressMgr(app).get()
        assert len(ingress.domains) == 1
        assert ingress.domains[0].path_prefix_list == ['/foo/']

        ingress = SubPathAppIngressMgr(app_2).get()
        assert len(ingress.domains) == 1
        assert ingress.domains[0].path_prefix_list == ['/bar/', '/foobar/']

    def test_subpath_transfer_fully(self, app):
        paths = ['/foo/']
        assign_subpaths(app, paths, 'foo-service')

        # Transfer all paths to app2
        app_2 = create_app()
        KNamespace(get_client_by_app(app_2)).get_or_create(app_2.namespace)
        assign_subpaths(app_2, paths, 'foo-service')

        with pytest.raises(AppEntityNotFound):
            SubPathAppIngressMgr(app).get()

        ingress = SubPathAppIngressMgr(app_2).get()
        assert len(ingress.domains) == 1
        assert ingress.domains[0].path_prefix_list == paths
