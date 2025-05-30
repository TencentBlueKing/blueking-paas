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

import atexit
import copy
import logging
import tempfile
from pathlib import Path
from typing import Callable, Dict

import pytest
import yaml
from django.conf import settings
from django.db import transaction
from kubernetes.client.apis import VersionApi
from kubernetes.client.exceptions import ApiException

from paas_wl.bk_app.applications.models import Build, BuildProcess, WlApp
from paas_wl.bk_app.processes.models import ProcessSpec, ProcessSpecPlan, initialize_default_proc_spec_plans
from paas_wl.infras.cluster.models import Cluster
from paas_wl.infras.resources.base.base import get_client_by_cluster_name, invalidate_global_configuration_pool
from paas_wl.infras.resources.base.kres import KCustomResourceDefinition, KNamespace
from paas_wl.utils.blobstore import S3Store, make_blob_store
from paasng.platform.applications.models import ModuleEnvironment
from tests.paas_wl.utils.basic import random_resource_name
from tests.paas_wl.utils.build import create_build_proc
from tests.paas_wl.utils.wl_app import create_wl_release
from tests.utils.cluster import CLUSTER_NAME_FOR_TESTING

logger = logging.getLogger(__name__)

# IDs for default "bk_app"'s ModuleEnv objects
DEFAULT_STAG_ENV_ID = 1
DEFAULT_PROD_ENV_ID = 2


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):  # noqa: PT004
    """Some initialization jobs before running tests."""
    with django_db_blocker.unblock():
        with transaction.atomic():
            # Clear cached configuration pool in case there are some stale configurations
            # in the pool.
            invalidate_global_configuration_pool()

        # The initialization in `processes.models` will not create default package plans in the TEST database,
        # it only creates the default plans in the non-test database(without the "test_" prefix).
        # So it's still required to initialize the default package plans here.
        initialize_default_proc_spec_plans()


@pytest.fixture(autouse=True, scope="session")
def _init_s3_bucket(request):
    if not request.config.getvalue("init_s3_bucket"):
        return

    store = make_blob_store(settings.BLOBSTORE_BUCKET_APP_SOURCE)
    if not isinstance(store, S3Store):
        return
    try:
        store.get_client().create_bucket(Bucket=store.bucket)
    except Exception:
        pass


@pytest.fixture(scope="session", autouse=True)
def crds_is_configured(django_db_setup, django_db_blocker):
    """Configure 'BkApp' and other CRDs when tests starts

    :return: Whether the CRDs are successfully configured
    """
    with django_db_blocker.unblock():
        cluster = Cluster.objects.get(name=CLUSTER_NAME_FOR_TESTING)
        client = get_client_by_cluster_name(cluster.name)
        version = VersionApi(client).get_code()

    # Minimal required version is 1.17
    if (int(version.major), int(version.minor)) < (1, 17):
        yield False
    else:
        crd_infos = [
            ("bkapps.paas.bk.tencent.com", "bk_app/cnative/specs/crd/bkapp_v1.yaml"),
            ("domaingroupmappings.paas.bk.tencent.com", "bk_app/cnative/specs/crd/domaingroupmappings_v1.yaml"),
        ]
        crd_client = KCustomResourceDefinition(client)

        for crd_name, path in crd_infos:
            logger.info("Configure CRD %s...", crd_name)
            body = yaml.safe_load((Path(__file__).parent / path).read_text())
            try:
                name = body["metadata"]["name"]
                crd_client.create_or_update(name=name, body=body)
            except ValueError as e:
                logger.warning("Unknown Exception raise from k8s client, but should be ignored. Detail: %s", e)
            except ApiException as e:
                # Ignore 409 conflicts error
                if e.status == 409:
                    pass

        yield True

        # Clean up CRDs
        for name, _ in crd_infos:
            crd_client.delete(name)


@pytest.fixture(autouse=True)
def _skip_when_no_crds(request, crds_is_configured):
    """Handle @pytest.mark.skip_when_no_crds, skip current test when mark is used
    and CRDs are not configured(from "crds_is_configured" fixture).
    """
    if request.keywords.get("skip_when_no_crds") and not crds_is_configured:
        pytest.skip("Skip test because CRDs is not configured")


@pytest.fixture()
def k8s_client():
    cluster = Cluster.objects.get(name=CLUSTER_NAME_FOR_TESTING)
    client = get_client_by_cluster_name(cluster.name)
    return client


@pytest.fixture()
def k8s_version(k8s_client):
    return VersionApi(k8s_client).get_code()


@pytest.fixture(scope="module")
def namespace_maker(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        cluster = Cluster.objects.get(name=CLUSTER_NAME_FOR_TESTING)
        k8s_client = get_client_by_cluster_name(cluster.name)
        k8s_version = VersionApi(k8s_client).get_code()

    class Maker:
        def __init__(self):
            self.block = False
            self.created_namespaces = []

        def make(self, ns):
            kres = KNamespace(k8s_client)
            obj, created = kres.get_or_create(ns)
            if created:
                self.created_namespaces.append(ns)
            # k8s 1.8 只起了 apiserver 模拟测试, 不支持 wait_for_default_sa.
            # 其他更高版本的集群为集成测试, 必须执行 wait_for_default_sa, 否则测试可能会出错
            if (int(k8s_version.major), int(k8s_version.minor)) > (1, 8):
                kres.wait_for_default_sa(ns)
            return obj, created

        def set_block(self):
            self.block = True

    maker = Maker()
    yield maker

    for ns in maker.created_namespaces:
        KNamespace(k8s_client).delete(ns)

    if maker.block:
        for ns in maker.created_namespaces:
            if (int(k8s_version.major), int(k8s_version.minor)) > (1, 8):
                KNamespace(k8s_client).wait_until_removed(ns)


@pytest.fixture(autouse=True)
def _auto_create_ns(request):
    """Create the k8s namespace when the mark is found, supported fixture:
    bk_stag_wl_app / bk_prod_wl_app
    """
    if not request.keywords.get("auto_create_ns"):
        yield
        return

    fixtures = ["bk_stag_wl_app", "bk_prod_wl_app", "wl_app"]
    used_fixtures = []
    for fixture in fixtures:
        if fixture in request.fixturenames:
            used_fixtures.append(fixture)
    if not used_fixtures:
        yield
        return

    namespace_maker = request.getfixturevalue("namespace_maker")
    for fixture in used_fixtures:
        app = request.getfixturevalue(fixture)
        namespace_maker.make(app.namespace)
    yield
    namespace_maker.set_block()


@pytest.fixture()
def resource_name() -> str:
    """A random resource name"""
    return random_resource_name()


@pytest.fixture()
def patch_ingress_config():
    """Patch ingress_config of the default cluster, usage:

    def test_foo(patch_ingress_config):
        patch_ingress_config(
            port_map: ...,
            app_root_domain: ...,
        )
        # Other test codes

    """
    cluster = Cluster.objects.get(name=CLUSTER_NAME_FOR_TESTING)
    orig_cfg = copy.deepcopy(cluster.ingress_config)

    def _patch_func(**kwargs):
        for k, v in kwargs.items():
            setattr(cluster.ingress_config, k, v)
        cluster.save(update_fields=["ingress_config"])

    yield _patch_func

    # Restore to original
    cluster.ingress_config = orig_cfg
    cluster.save(update_fields=["ingress_config"])


def get_cluster_with_hook(hook_func: Callable) -> Callable:
    """Modify the original get_cluster function with extra hooks"""

    def _wrapped(app: WlApp) -> Cluster:
        from paas_wl.infras.cluster.utils import get_cluster_by_app

        cluster = get_cluster_by_app(app)
        cluster = hook_func(cluster)
        return cluster

    return _wrapped


@atexit.register
def clear_kubernetes_dynamic_discoverer_cache():
    # Delete all discoverer caches to ensure that the next test run is not affected after switching kubernetes clusters
    for f in Path(tempfile.gettempdir()).glob("osrcp-*.json"):
        f.unlink(missing_ok=True)


@pytest.fixture()
def default_process_spec_plan():
    return ProcessSpecPlan.objects.first()


@pytest.fixture()
def set_structure(default_process_spec_plan):
    """A factory fixture, returns a function which updates app structure"""

    def handler(app, procfile: Dict, plan: ProcessSpecPlan = default_process_spec_plan):
        ProcessSpec.objects.filter(engine_app_id=app.uuid).delete()
        for proc, replicas in procfile.items():
            ProcessSpec.objects.create(
                name=proc, target_replicas=replicas, engine_app_id=app.uuid, plan=plan, tenant_id=app.tenant_id
            )

    return handler


@pytest.fixture()
def bk_stag_wl_app(bk_stag_env, _with_wl_apps):
    return bk_stag_env.wl_app


@pytest.fixture()
def bk_prod_wl_app(bk_prod_env, _with_wl_apps):
    return bk_prod_env.wl_app


@pytest.fixture()
def wl_app(bk_stag_wl_app) -> WlApp:
    return bk_stag_wl_app


@pytest.fixture()
def wl_release(wl_app):
    return create_wl_release(
        wl_app=wl_app,
        release_params={
            "version": 5,
            "procfile": {"web": "python manage.py runserver", "worker": "python manage.py celery"},
        },
    )


@pytest.fixture()
def wl_dirty_release(wl_app):
    return create_wl_release(
        wl_app=wl_app,
        release_params={"version": 1, "build": None},
    )


@pytest.fixture()
def build_proc(wl_app) -> BuildProcess:
    """A new BuildProcess object with random info"""
    env = ModuleEnvironment.objects.get(engine_app_id=wl_app.uuid)
    return create_build_proc(env)


@pytest.fixture()
def wl_build(bk_stag_wl_app, bk_user) -> Build:
    build_params = {
        "owner": bk_user.pk,
        "app": bk_stag_wl_app,
        "slug_path": "",
        "source_type": "foo",
        "branch": "bar",
        "revision": "1",
        "artifact_type": "slug",
    }
    return Build.objects.create(tenant_id=bk_stag_wl_app.tenant_id, **build_params)
