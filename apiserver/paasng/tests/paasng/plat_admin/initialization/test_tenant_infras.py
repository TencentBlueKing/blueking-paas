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

import copy
import json
from pathlib import Path
from typing import Any, Iterator
from unittest import mock

import pytest
import yaml
from django.core.management import CommandError, call_command
from django_dynamic_fixture import G

from paas_wl.infras.cluster.constants import ClusterAllocationPolicyType
from paas_wl.infras.cluster.models import (
    APIServer,
    Cluster,
    ClusterAllocationPolicy,
    ClusterAppImageRegistry,
    ClusterComponent,
)
from paasng.accessories.log.models import TenantLogConfig
from paasng.accessories.servicehub.binding_policy.manager import SvcBindingPolicyManager
from paasng.accessories.servicehub.manager import mixed_plan_mgr, mixed_service_mgr
from paasng.accessories.services.models import Plan, PreCreatedInstance, Service, ServiceCategory
from paasng.plat_admin.initialization.tenant_infras import initializer as initializer_module
from paasng.plat_admin.initialization.tenant_infras.initializer import (
    Action,
    InitializationError,
    Record,
    TenantInfrasInitializer,
)
from paasng.plat_admin.initialization.tenant_infras.serializers import TenantInfrasSLZ
from tests.utils.helpers import generate_random_string

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

INITIALIZER_MODULE = "paasng.plat_admin.initialization.tenant_infras.initializer"


@pytest.fixture()
def tenant_id() -> str:
    return f"t-{generate_random_string(8)}"


@pytest.fixture()
def pool_service() -> Service:
    """资源池类的本地服务（类似 redis）"""
    return G(
        Service,
        name=f"redis-{generate_random_string(6)}",
        category=G(ServiceCategory),
        logo_b64="dummy",
        config={"provider_name": "pool"},
    )


@pytest.fixture()
def normal_service() -> Service:
    """非资源池类的本地服务"""
    return G(Service, name=f"mysql-{generate_random_string(6)}", category=G(ServiceCategory), logo_b64="dummy")


@pytest.fixture(autouse=True)
def mock_k8s_accessible() -> Iterator[mock.MagicMock]:
    with mock.patch(f"{INITIALIZER_MODULE}.check_k8s_accessible", return_value=True) as mocked:
        yield mocked


@pytest.fixture()
def raw_config(tenant_id, pool_service, normal_service) -> dict[str, Any]:
    cluster_name = f"c-{generate_random_string(8)}"
    return {
        "tenant_id": tenant_id,
        "clusters": [
            {
                "name": cluster_name,
                "description": "tenant cluster",
                "cluster_source": "native_k8s",
                "api_address_type": "custom",
                "api_servers": ["https://10.0.0.1:6443"],
                "auth_type": "token",
                "token": "secret-token",
                "container_log_dir": "/var/lib/docker/containers",
                "elastic_search_config": {
                    "scheme": "http",
                    "host": "es.example.com",
                    "port": 9200,
                    "username": "elastic",
                    "password": "es-pwd",
                },
                "app_image_registry": {
                    "host": "mirrors.example.com",
                    "skip_tls_verify": False,
                    "namespace": "bkapps",
                    "username": "bkapps",
                    "password": "registry-pwd",
                },
                "app_address_type": "subdomain",
                "app_domains": [{"name": "apps.example.com", "https_enabled": True}],
            }
        ],
        "cluster_allocation_policy": {
            "type": "uniform",
            "allocation_policy": {"env_specific": False, "clusters": [cluster_name]},
        },
        "services": {
            normal_service.name: {
                "plans": [{"name": "default", "description": "default plan", "config": {"host": "db"}}],
            },
            pool_service.name: {
                "plans": [
                    {
                        "name": "0shared",
                        "description": "shared",
                        "pre_created_instances": [
                            {"config": {}, "credentials": {"host": "redis-0", "port": 6379, "password": "p0"}},
                            {"config": {}, "credentials": {"host": "redis-1", "port": 6379, "password": "p1"}},
                        ],
                    },
                    {"name": "1exclusive", "description": "exclusive"},
                ],
            },
        },
        "log_config": {"storage_cluster_id": 3},
    }


def run_init(raw: dict[str, Any], dry_run: bool = False) -> list[Record]:
    slz = TenantInfrasSLZ(data=copy.deepcopy(raw))
    slz.is_valid(raise_exception=True)
    return TenantInfrasInitializer(slz.validated_data, dry_run=dry_run).run()


def actions(records: list[Record]) -> dict[str, str]:
    return {f"{r.kind}:{r.target}": r.action for r in records}


class TestInitialize:
    def test_dry_run(self, raw_config, tenant_id):
        records = run_init(raw_config, dry_run=True)

        assert records
        assert all(r.action == Action.CREATE for r in records)
        assert not Cluster.objects.filter(name=raw_config["clusters"][0]["name"]).exists()
        assert not ClusterAllocationPolicy.objects.filter(tenant_id=tenant_id).exists()
        assert not Plan.objects.filter(tenant_id=tenant_id).exists()
        assert not TenantLogConfig.objects.filter(tenant_id=tenant_id).exists()

    def test_apply(self, raw_config, tenant_id, pool_service, normal_service):
        records = run_init(raw_config)
        assert all(r.action == Action.CREATE for r in records)

        cluster = Cluster.objects.get(name=raw_config["clusters"][0]["name"])
        assert cluster.tenant_id == tenant_id
        assert cluster.available_tenant_ids == [tenant_id]
        assert cluster.token_value == "secret-token"
        assert cluster.ingress_config.app_root_domains[0].name == "apps.example.com"
        assert list(APIServer.objects.filter(cluster=cluster).values_list("host", flat=True)) == [
            "https://10.0.0.1:6443"
        ]
        assert ClusterComponent.objects.filter(cluster=cluster).exists()
        assert ClusterAppImageRegistry.objects.get(cluster=cluster).host == "mirrors.example.com"

        policy = ClusterAllocationPolicy.objects.get(tenant_id=tenant_id)
        assert policy.type == ClusterAllocationPolicyType.UNIFORM
        assert policy.allocation_policy.clusters == [cluster.name]

        assert Plan.objects.filter(service=normal_service, tenant_id=tenant_id, name="default").exists()
        shared_plan = Plan.objects.get(service=pool_service, tenant_id=tenant_id, name="0shared")
        instances = PreCreatedInstance.objects.filter(plan=shared_plan)
        assert sorted(json.loads(i.credentials)["host"] for i in instances) == ["redis-0", "redis-1"]
        assert all(i.tenant_id == tenant_id for i in instances)

        # 默认统一分配本次声明的所有可用方案
        pool_service_obj = mixed_service_mgr.get(pool_service.uuid)
        cfg = SvcBindingPolicyManager(pool_service_obj, tenant_id).get_comb_cfg()
        assert cfg is not None
        assert cfg.allocation_policy is not None
        assert set(cfg.allocation_policy.plans or []) == {
            str(p.uuid) for p in Plan.objects.filter(service=pool_service, tenant_id=tenant_id)
        }

        assert TenantLogConfig.objects.get(tenant_id=tenant_id).storage_cluster_id == 3

    def test_rerun_skips_existing(self, raw_config, tenant_id, normal_service):
        run_init(raw_config)
        raw_config["clusters"][0]["description"] = "updated"
        raw_config["services"][normal_service.name]["plans"][0]["description"] = "updated plan"
        records = run_init(raw_config)

        assert all(r.action == Action.SKIP for r in records)
        assert Cluster.objects.get(name=raw_config["clusters"][0]["name"]).description == "tenant cluster"
        assert Plan.objects.get(service=normal_service, tenant_id=tenant_id).description == "default plan"
        assert PreCreatedInstance.objects.filter(tenant_id=tenant_id).count() == 2

    def test_rerun_appends_new_instance(self, raw_config, tenant_id, pool_service):
        run_init(raw_config)
        raw_config["services"][pool_service.name]["plans"][0]["pre_created_instances"].append(
            {"config": {}, "credentials": {"host": "redis-2", "port": 6379, "password": "p2"}}
        )
        records = run_init(raw_config)

        assert actions(records)[f"pre_created_instance:{pool_service.name}/0shared/redis-2:6379"] == Action.CREATE
        assert PreCreatedInstance.objects.filter(tenant_id=tenant_id).count() == 3

    def test_instance_count(self, raw_config, tenant_id, pool_service):
        instances = raw_config["services"][pool_service.name]["plans"][0]["pre_created_instances"]
        instances[0]["count"] = 3
        run_init(raw_config)
        assert PreCreatedInstance.objects.filter(tenant_id=tenant_id).count() == 4

        target = f"pre_created_instance:{pool_service.name}/0shared/redis-0:6379"
        instances[0]["count"] = 5
        records = run_init(raw_config)
        assert actions(records)[target] == Action.CREATE
        assert PreCreatedInstance.objects.filter(tenant_id=tenant_id).count() == 6

        # 数量减少时不删除已有实例
        instances[0]["count"] = 2
        records = run_init(raw_config)
        assert actions(records)[target] == Action.SKIP
        assert PreCreatedInstance.objects.filter(tenant_id=tenant_id).count() == 6

    def test_cluster_inaccessible(self, raw_config, tenant_id, mock_k8s_accessible):
        mock_k8s_accessible.return_value = False

        with pytest.raises(InitializationError, match="not accessible"):
            run_init(raw_config)
        assert not Cluster.objects.filter(name=raw_config["clusters"][0]["name"]).exists()
        assert not Plan.objects.filter(tenant_id=tenant_id).exists()

    def test_service_failure_isolated(self, raw_config, tenant_id, pool_service, normal_service):
        origin_create = mixed_plan_mgr.create

        def _create(service, plan_data):
            if service.name == normal_service.name:
                raise RuntimeError("remote service unavailable")
            return origin_create(service, plan_data=plan_data)

        with mock.patch(f"{INITIALIZER_MODULE}.mixed_plan_mgr.create", side_effect=_create):
            initializer_records = run_init(raw_config)

        failed = [r for r in initializer_records if r.action == Action.FAILED]
        assert [(r.target, r.detail) for r in failed] == [(normal_service.name, "remote service unavailable")]
        assert Plan.objects.filter(service=pool_service, tenant_id=tenant_id).count() == 2
        assert TenantLogConfig.objects.filter(tenant_id=tenant_id).exists()

    def test_shared_cluster(self, raw_config, tenant_id):
        shared = G(Cluster, name=f"s-{generate_random_string(8)}", tenant_id="other", available_tenant_ids=["other"])
        raw_config["shared_clusters"] = [shared.name]
        raw_config["cluster_allocation_policy"]["allocation_policy"]["clusters"] = [shared.name]

        run_init(raw_config)

        shared.refresh_from_db()
        assert shared.available_tenant_ids == ["other", tenant_id]
        assert ClusterAllocationPolicy.objects.get(tenant_id=tenant_id).allocation_policy.clusters == [shared.name]


class TestValidation:
    def test_example_config(self):
        example = Path(initializer_module.__file__).parent / "example.yaml"
        slz = TenantInfrasSLZ(data=yaml.safe_load(example.read_text()))
        assert slz.is_valid(), slz.errors

    def test_cluster_owned_by_other_tenant(self, raw_config):
        G(Cluster, name=raw_config["clusters"][0]["name"], tenant_id="other")

        slz = TenantInfrasSLZ(data=raw_config)
        assert not slz.is_valid()
        assert "shared_clusters" in str(slz.errors["clusters"])

    def test_instances_on_non_pool_service(self, raw_config, normal_service):
        raw_config["services"][normal_service.name]["plans"][0]["pre_created_instances"] = [
            {"config": {}, "credentials": {"host": "x"}}
        ]
        with pytest.raises(InitializationError, match="not a resource pool service"):
            run_init(raw_config, dry_run=True)

    def test_duplicated_instances(self, raw_config, pool_service):
        instances = raw_config["services"][pool_service.name]["plans"][0]["pre_created_instances"]
        instances.append(copy.deepcopy(instances[0]))

        slz = TenantInfrasSLZ(data=raw_config)
        assert not slz.is_valid()
        assert "count" in str(slz.errors)

    def test_unknown_binding_plan(self, raw_config, normal_service):
        raw_config["services"][normal_service.name]["binding_policy"] = {"plans": ["not-exists"]}
        with pytest.raises(InitializationError, match="not-exists"):
            run_init(raw_config, dry_run=True)

    def test_unknown_allocation_cluster(self, raw_config):
        raw_config["cluster_allocation_policy"]["allocation_policy"]["clusters"] = ["not-exists-cluster"]
        with pytest.raises(InitializationError, match="not-exists-cluster"):
            run_init(raw_config, dry_run=True)

    def test_unknown_service(self, raw_config):
        raw_config["services"]["not-exists-svc"] = {"plans": []}
        with pytest.raises(InitializationError, match="not-exists-svc"):
            run_init(raw_config, dry_run=True)


class TestCommand:
    def test_dry_run_by_default(self, raw_config, tenant_id, tmp_path, capsys):
        path = tmp_path / "tenant.yaml"
        path.write_text(yaml.safe_dump(raw_config))

        call_command("init_tenant_infras", "-f", str(path))
        assert "DRY-RUN" in capsys.readouterr().out
        assert not Plan.objects.filter(tenant_id=tenant_id).exists()

        call_command("init_tenant_infras", "-f", str(path), "--dry-run=false")
        assert Cluster.objects.get(name=raw_config["clusters"][0]["name"]).token_value == "secret-token"

    def test_invalid_config(self, tmp_path):
        path = tmp_path / "tenant.yaml"
        path.write_text(yaml.safe_dump({"services": {}}))

        with pytest.raises(CommandError, match="tenant_id"):
            call_command("init_tenant_infras", "-f", str(path))
