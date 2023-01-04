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
import copy
import logging
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Dict, List, Optional
from unittest import mock

import pytest
import yaml
from django.conf import settings
from django.db import transaction
from django.utils.crypto import get_random_string
from kubernetes.client.apis import VersionApi
from kubernetes.client.exceptions import ApiException
from rest_framework.test import APIClient

from paas_wl.cluster.constants import ClusterFeatureFlag, ClusterType
from paas_wl.cluster.models import APIServer, Cluster
from paas_wl.cluster.utils import get_default_cluster_by_region
from paas_wl.platform.applications.constants import ApplicationType
from paas_wl.platform.applications.models import Build, EngineApp
from paas_wl.platform.applications.struct_models import Application, Module, ModuleEnv, StructuredApp
from paas_wl.resources.base.base import get_client_by_cluster_name
from paas_wl.resources.base.kres import KCustomResourceDefinition, KNamespace
from paas_wl.utils.blobstore import S3Store, make_blob_store
from paas_wl.workloads.processes.models import ProcessSpec, ProcessSpecPlan
from tests.utils.app import create_app
from tests.utils.auth import create_user
from tests.utils.basic import random_resource_name
from tests.utils.build_process import random_fake_bp

logger = logging.getLogger(__name__)

# IDs for default "bk_app"'s ModuleEnv objects
DEFAULT_STAG_ENV_ID = 1
DEFAULT_PROD_ENV_ID = 2


def pytest_addoption(parser):
    parser.addoption(
        "--init-s3-bucket", dest="init_s3_bucket", action="store_true", default=False, help="是否需要执行 s3 初始化流程"
    )
    parser.addoption("--run-e2e-test", dest="run_e2e_test", action="store_true", default=False, help="是否执行 e2e 测试")


@pytest.fixture(scope='session', autouse=True)
def crds_is_configured(django_db_setup, django_db_blocker):
    """Configure 'BkApp' and other CRDs when tests starts

    :return: Whether the CRDs are successfully configured
    """
    with django_db_blocker.unblock():
        client = get_client_by_cluster_name(get_default_cluster_by_region(settings.FOR_TESTS_DEFAULT_REGION).name)
        version = VersionApi(client).get_code()

    # Minimal required version is 1.17
    if (int(version.major), int(version.minor)) < (1, 17):
        yield False
    else:
        crd_infos = [
            ("bkapps.paas.bk.tencent.com", "cnative/specs/crd/bkapp_v1.yaml"),
            ("domaingroupmappings.paas.bk.tencent.com", "cnative/specs/crd/domaingroupmappings_v1.yaml"),
        ]
        crd_client = KCustomResourceDefinition(client)

        for name, path in crd_infos:
            logger.info('Configure CRD %s...', name)
            body = yaml.safe_load((Path(__file__).parent / path).read_text())
            try:
                name = body['metadata']['name']
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
    if request.keywords.get('skip_when_no_crds'):
        if not crds_is_configured:
            pytest.skip('Skip test because CRDs is not configured')


@pytest.fixture(autouse=True, scope="session")
def init_s3_bucket(request):
    if not request.config.getvalue("init_s3_bucket"):
        return

    store = make_blob_store(settings.BLOBSTORE_S3_BUCKET_NAME)
    if not isinstance(store, S3Store):
        return
    try:
        store.get_client().create_bucket(Bucket=store.bucket)
    except Exception:
        pass


@pytest.fixture
def app() -> EngineApp:
    """Return a new App object with random info"""
    return create_app()


@pytest.fixture
def k8s_client(settings):
    client = get_client_by_cluster_name(get_default_cluster_by_region(settings.FOR_TESTS_DEFAULT_REGION).name)
    return client


@pytest.fixture
def k8s_version(k8s_client):
    return VersionApi(k8s_client).get_code()


@pytest.fixture(scope="module")
def namespace_maker(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        k8s_client = get_client_by_cluster_name(get_default_cluster_by_region(settings.FOR_TESTS_DEFAULT_REGION).name)
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
                KNamespace(k8s_client).wait_for_delete(ns)


@pytest.fixture(autouse=True)
def _auto_create_ns(request):
    """Create the k8s namespace when the mark is found, supported fixture:
    app / bk_stag_engine_app
    """
    if not request.keywords.get('auto_create_ns'):
        yield
        return

    if "bk_stag_engine_app" in request.fixturenames:
        app = request.getfixturevalue("bk_stag_engine_app")
    elif "app" in request.fixturenames:
        app = request.getfixturevalue("app")
    else:
        yield
        return

    namespace_maker = request.getfixturevalue("namespace_maker")
    namespace_maker.make(app.namespace)
    yield
    namespace_maker.set_block()


@pytest.fixture
def bp(app):
    """Return a new BuildProcess object with random info"""
    return random_fake_bp(app)


@pytest.fixture
def resource_name() -> str:
    """A random resource name"""
    return random_resource_name()


# A random cluster name for running unittests
CLUSTER_NAME_FOR_TESTING = get_random_string(6)


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Create default cluster for testing"""
    with django_db_blocker.unblock():
        with transaction.atomic():
            cluster = create_default_cluster()
            setup_default_client(cluster)

        from paas_wl.workloads.processes.models import initialize_default_proc_spec_plans

        # The initialization in `processes.models` will not create default package plans in the TEST database,
        # it only creates the default plans in the non-test database(without the "test_" prefix).
        # So it's still required to initialize the default package plans here.
        initialize_default_proc_spec_plans()


def create_default_cluster():
    """Destroy all existing clusters and create a default one"""
    Cluster.objects.all().delete()
    cluster = Cluster.objects.register_cluster(
        name=CLUSTER_NAME_FOR_TESTING,
        region=settings.FOR_TESTS_DEFAULT_REGION,
        is_default=True,
        ingress_config={
            "app_root_domains": [{"name": "example.com"}],
            "sub_path_domains": [{"name": "example.com"}],
            "default_ingress_domain_tmpl": "%s.unittest.com",
            "frontend_ingress_ip": "0.0.0.0",
            "port_map": {"http": "80", "https": "443"},
        },
        annotations={
            "bcs_cluster_id": "",
            "bcs_project_id": "",
        },
        ca_data=settings.FOR_TESTS_CLUSTER_CONFIG["ca_data"],
        cert_data=settings.FOR_TESTS_CLUSTER_CONFIG["cert_data"],
        key_data=settings.FOR_TESTS_CLUSTER_CONFIG["key_data"],
        feature_flags=ClusterFeatureFlag.get_default_flags_by_cluster_type(ClusterType.NORMAL),
    )
    APIServer.objects.get_or_create(
        host=settings.FOR_TESTS_CLUSTER_CONFIG["url"],
        cluster=cluster,
        defaults=dict(
            overridden_hostname=settings.FOR_TESTS_CLUSTER_CONFIG["force_domain"],
        ),
    )
    return cluster


@pytest.fixture
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
        cluster.save(update_fields=['ingress_config'])

    yield _patch_func

    # Restore to original
    cluster.ingress_config = orig_cfg
    cluster.save(update_fields=['ingress_config'])


def setup_default_client(cluster: Cluster):
    """setup the default config for those client created by `kubernetes.client.ApiClient`"""
    # TODO: 待重构, 让 BaseKresource 不再接受 ModuleType 类型的 client
    get_client_by_cluster_name(cluster.name)


def get_cluster_with_hook(hook_func: Callable) -> Callable:
    """Modify the original get_cluster function with extra hooks"""

    def _wrapped(app: EngineApp) -> Cluster:
        from paas_wl.cluster.utils import get_cluster_by_app

        cluster = get_cluster_by_app(app)
        cluster = hook_func(cluster)
        return cluster

    return _wrapped


@contextmanager
def override_cluster_ingress_attrs(attrs):
    """Context manager which updates app's `cluster.ingress_config`"""

    def _hook_set_sub_path_domain(cluster):
        for key, value in attrs.items():
            setattr(cluster.ingress_config, key, value)
        cluster.save()
        cluster.refresh_from_db()
        return cluster

    # Mock all related occurrences
    with mock.patch(
        'paas_wl.networking.ingress.managers.misc.get_cluster_by_app',
        get_cluster_with_hook(_hook_set_sub_path_domain),
    ), mock.patch(
        'paas_wl.networking.ingress.managers.subpath.get_cluster_by_app',
        get_cluster_with_hook(_hook_set_sub_path_domain),
    ):
        yield


@pytest.fixture(autouse=True)
def clear_kubernetes_dynamic_discoverer_cache():
    # delete all discoverer cache files to ensure tests successful of the multiple kubernetes clusters
    for f in Path(tempfile.gettempdir()).glob("osrcp-*.json"):
        f.unlink()


@pytest.fixture
def api_client(request, bk_user):
    """Return an authenticated client"""
    client = APIClient()
    client.force_authenticate(user=bk_user)
    return client


@pytest.fixture
def bk_user():
    user = create_user(username="bk_somebody")
    user.is_superuser = True
    return user


@pytest.fixture
def fake_app(bk_user, app):
    app.owner = str(bk_user)
    app.structure = {"web": 1, "worker": 1}
    app.save()
    return app


@pytest.fixture
def default_process_spec_plan():
    return ProcessSpecPlan.objects.first()


@pytest.fixture
def set_structure(default_process_spec_plan):
    def handler(app, procfile: Dict, plan: ProcessSpecPlan = default_process_spec_plan):
        ProcessSpec.objects.filter(engine_app_id=app.uuid).delete()
        for proc, replicas in procfile.items():
            ProcessSpec.objects.create(name=proc, target_replicas=replicas, engine_app_id=app.uuid, plan=plan)

    return handler


@pytest.fixture
def fake_simple_build(fake_app, bk_user):
    build_params = {
        "owner": bk_user,
        "app": fake_app,
        "slug_path": "",
        "source_type": "zzz",
        "branch": "dsdf",
        "revision": "asdf",
        "procfile": {"web": "legacycommand manage.py runserver", "worker": "python manage.py celery"},
    }
    return Build.objects.create(**build_params)


@pytest.fixture
def bk_app():
    """A random Application object"""
    # Use lower case only because the code/name might be used for Kubernetes resource name
    code = get_random_string(6).lower()
    return Application(
        id=uuid.uuid4(), type=ApplicationType.DEFAULT, region=settings.FOR_TESTS_DEFAULT_REGION, name=code, code=code
    )


@pytest.fixture
def bk_module(bk_app):
    """A random Module object"""
    return Module(id=uuid.uuid4(), application=bk_app, name='default')


@pytest.fixture
def bk_stag_env(request, bk_app, bk_module):
    """A random ModuleEnv object"""
    return create_env(request, bk_app, bk_module, 'stag')


@pytest.fixture
def bk_stag_engine_app(bk_stag_env) -> EngineApp:
    return EngineApp.objects.get_by_env(bk_stag_env)


@pytest.fixture
def bk_prod_env(request, bk_app, bk_module):
    """A random ModuleEnv object"""
    return create_env(request, bk_app, bk_module, 'prod')


@pytest.fixture
def bk_prod_engine_app(bk_prod_env) -> EngineApp:
    return EngineApp.objects.get_by_env(bk_prod_env)


@pytest.fixture(autouse=True)
def _mock_get_structured_app(request, bk_app, bk_module):
    """Handle "mock_get_structured_app" mark, auto mock `get_structured_app`
    function call to return response related with current fixture data.
    """
    if request.keywords.get('mock_get_structured_app'):
        # Get bk_stag_env and bk_prod_env fixture dynamically instead of reference
        # directly to avoid requiring db access every time.
        stag_env = request.getfixturevalue("bk_stag_env")
        prod_env = request.getfixturevalue("bk_prod_env")

        structured_app = StructuredApp.from_json_data(
            make_structured_app_data(
                bk_app,
                default_module_id=str(bk_module.id),
                engine_app_ids=[str(stag_env.engine_app_id), str(prod_env.engine_app_id)],
            )
        )
        # Patch multiple occurrences
        with mock.patch(
            "paas_wl.platform.applications.struct_models.get_structured_app", return_value=structured_app
        ), mock.patch("paas_wl.platform.applications.models_utils.get_structured_app", return_value=structured_app):
            yield
    else:
        yield


def create_env(request, bk_app, bk_module, environment: str) -> ModuleEnv:
    # Use fixed ID
    id_map = {'stag': DEFAULT_STAG_ENV_ID, 'prod': DEFAULT_PROD_ENV_ID}
    engine_app = create_app()
    return ModuleEnv(
        id=id_map[environment],
        application=bk_app,
        module=bk_module,
        environment=environment,
        engine_app_id=engine_app.uuid,
        is_offlined=False,
    )


@pytest.fixture
def cnative_bk_app(bk_app):
    """A random Application object, type is "cloud-native" """
    bk_app.type = ApplicationType.CLOUD_NATIVE
    return bk_app


def make_structured_app_data(
    application: Application,
    default_module_id: Optional[str] = None,
    environment_ids: Optional[List[int]] = None,
    engine_app_ids: Optional[List[str]] = None,
):
    """Make a raw structured application data with one default module, receives optional "module_id"
    parameters.
    """
    default_module_id = default_module_id or str(uuid.uuid4())
    environment_ids = environment_ids or [DEFAULT_STAG_ENV_ID, DEFAULT_PROD_ENV_ID]
    engine_app_ids = engine_app_ids or [str(uuid.uuid4()), str(uuid.uuid4())]
    return {
        "application": {
            "id": str(application.id),
            "type": application.type,
            "region": application.region,
            "code": application.code,
            "name": application.name,
        },
        "modules": [{"id": str(default_module_id), "name": "default"}],
        "envs": [
            {
                "id": environment_ids[0],
                "environment": "stag",
                "module_id": default_module_id,
                "engine_app_id": engine_app_ids[0],
                "is_offlined": False,
            },
            {
                "id": environment_ids[1],
                "environment": "prod",
                "module_id": default_module_id,
                "engine_app_id": engine_app_ids[1],
                "is_offlined": False,
            },
        ],
    }
