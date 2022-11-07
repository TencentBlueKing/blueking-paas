import logging
from pathlib import Path
from typing import Dict
from unittest import mock

import pytest
import yaml
from kubernetes.client import ApiextensionsV1Api
from kubernetes.client.exceptions import ApiException

from paas_wl.cnative.specs.constants import (
    IMAGE_CREDENTIALS_REF_ANNO_KEY,
    DeployStatus,
    MResConditionType,
    MResPhaseType,
)
from paas_wl.cnative.specs.credentials import ImageCredentialsManager
from paas_wl.cnative.specs.models import EnvResourcePlanner
from paas_wl.cnative.specs.resource import MresConditionParser, deploy, get_mres_from_cluster
from paas_wl.platform.applications.models import EngineApp
from paas_wl.resources.base.base import get_client_by_cluster_name
from paas_wl.workloads.images.constants import KUBE_RESOURCE_NAME as PULL_SECRET_NAME
from tests.cnative.specs.utils import create_condition, create_res_with_conds
from tests.utils.mocks.platform import FakePlatformSvcClient

pytestmark = pytest.mark.django_db
logger = logging.getLogger(__name__)


class TestMresConditionDetector:
    @pytest.mark.parametrize(
        "mres, expected_status",
        [
            (create_res_with_conds([]), DeployStatus.PENDING),
            (
                create_res_with_conds([create_condition(MResConditionType.APP_AVAILABLE)]),
                DeployStatus.PROGRESSING,
            ),
            (
                create_res_with_conds(
                    [create_condition(MResConditionType.APP_AVAILABLE, "True")], MResPhaseType.AppRunning
                ),
                DeployStatus.READY,
            ),
            (
                create_res_with_conds(
                    [create_condition(MResConditionType.ADDONS_PROVISIONED, "False")], MResPhaseType.AppFailed
                ),
                DeployStatus.ERROR,
            ),
            (
                create_res_with_conds(
                    [
                        create_condition(MResConditionType.ADDONS_PROVISIONED, "False"),
                        create_condition(MResConditionType.APP_AVAILABLE, "True"),
                    ],
                    MResPhaseType.AppFailed,
                ),
                DeployStatus.READY,
            ),
        ],
    )
    def test_detect(self, mres, expected_status):
        s = MresConditionParser(mres).detect_state()
        assert s.status == expected_status


class TestBkAppClusterOperator:
    """测试在集群中操作 bkapp 资源"""

    @pytest.fixture
    def setup_crd(self, k8s_client, k8s_version, settings):
        if (int(k8s_version.major), int(k8s_version.minor)) <= (1, 16):
            pytest.skip("不支持版本 <1.16 的 k8s 集群")

        crd_infos = [
            ("bkapps.paas.bk.tencent.com", "bkapp_v1.yaml"),
            ("domaingroupmappings.paas.bk.tencent.com", "domaingroupmappings_v1.yaml"),
        ]

        client = ApiextensionsV1Api(k8s_client)

        for name, path in crd_infos:
            body = yaml.load((Path(__file__).parent / "crd" / path).read_text())

            try:
                client.create_custom_resource_definition(body)
            except ValueError as e:
                logger.warning("Unknown Exception raise from k8s client, but should be ignored. Detail: %s", e)
            except ApiException as e:
                if e.status == 409:
                    # CRD 已存在, 忽略
                    pass

        yield

        for name, _ in crd_infos:
            client.delete_custom_resource_definition(name)

    @pytest.fixture
    def setup_clients(self):
        with mock.patch('paas_wl.platform.external.client._global_plat_client', new=FakePlatformSvcClient()):
            yield

    def test_deploy_and_get_status(self, bk_app, bk_stag_env, setup_crd, setup_clients):
        manifest: Dict = {
            "apiVersion": "paas.bk.tencent.com/v1alpha1",
            "kind": "BkApp",
            "metadata": {"name": bk_app.code, "annotations": {IMAGE_CREDENTIALS_REF_ANNO_KEY: "true"}},
            "spec": {
                "processes": [
                    {"name": "web", "replicas": 1, "image": "nginx:latest", "cpu": "100m", "memory": "100Mi"}
                ],
                "hooks": {"preRelease": {"command": ["/bin/echo"], "args": ["Hello"]}},
                "configuration": {"env": []},
            },
        }

        with mock.patch('paas_wl.cnative.specs.resource.KNamespace.wait_for_default_sa'):
            ret = deploy(bk_stag_env, manifest)

        assert ret["spec"]["processes"][0]["name"] == "web"
        assert get_mres_from_cluster(bk_stag_env) is not None

        planer = EnvResourcePlanner(bk_stag_env)
        engine_app = EngineApp.objects.get_by_env(bk_stag_env)
        with get_client_by_cluster_name(planer.cluster.name) as client:
            assert ImageCredentialsManager(client).get(engine_app, PULL_SECRET_NAME) is not None

        # 修改进程配置信息，再次部署到集群
        manifest["spec"]["processes"].append(
            {"name": "worker", "replicas": 1, "image": "busybox:latest", "cpu": "100m", "memory": "100Mi"}
        )
        ret = deploy(bk_stag_env, manifest)
        assert ret["spec"]["processes"][1]["name"] == "worker"
