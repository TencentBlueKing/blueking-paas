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
from typing import Any

import pytest
from django.test import override_settings
from kubernetes.client.exceptions import ApiException

from paas_wl.infras.cluster.shim import EnvClusterService
from paas_wl.workloads.release_controller.entities import SecretFileMount
from paasng.infras.kms.client import CredentialInfo, KMSClient, KMSScope, ServiceAccountAuth
from paasng.infras.kms.exceptions import (
    KMSAPIError,
    KMSConfigError,
    KMSCredentialMismatchError,
    KMSRequestError,
    KMSSecretNotReadyError,
    KMSValidationError,
)
from paasng.platform.engine.configurations.kms.provisioner import (
    KMSSaaSSettings,
    KMSSecretProvisioner,
    create_kms_config_version,
    load_kms_settings,
    provision_kms_secret,
)
from paasng.platform.engine.configurations.kms.recycler import (
    RECYCLING_REASON,
    recycle_module_env_kms_config_versions,
    recycle_stale_kms_config_versions,
)
from paasng.platform.engine.constants import JobStatus, KMSConfigVersionStatus
from paasng.platform.engine.models import Deployment, KMSConfigVersion
from tests.paasng.platform.engine.setup_utils import create_fake_deployment

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])

CLUSTER_NAME = "test-cluster"
ES_API_VERSION = "external-secrets.io/v1beta1"
SENSITIVE_ENV = {"DB_PASSWORD": "s3cret-value-xyz", "API_TOKEN": "tok-abc-123"}


class FakeKMS(KMSClient):
    """内存中的 KMS 替身。不调用父类构造函数，未覆盖的方法会因缺少会话而失败"""

    def __init__(self) -> None:
        self.plaintexts: list[str] = []
        self.credentials: dict[str, CredentialInfo] = {}
        self.envelopes: dict[str, str] = {}
        self.created: list[str] = []
        self.deleted_ids: list[int] = []
        # 创建请求已生效，但调用方收到网络错误
        self.create_outcome_unknown = False
        self.fail_create_with: Exception | None = None
        self._next_id = 100

    def encrypt_credential_value(self, plaintext: str) -> str:
        self.plaintexts.append(plaintext)
        return f"envelope-{len(self.plaintexts)}"

    def find_credential(self, *, scope: KMSScope, name: str) -> CredentialInfo | None:
        return self.credentials.get(name)

    def create_credential_from_envelope(
        self,
        *,
        scope: KMSScope,
        name: str,
        envelope: str,
        auth: ServiceAccountAuth,
        description: str = "",
        annotation: str = "",
    ) -> int:
        if self.fail_create_with is not None:
            raise self.fail_create_with
        if name in self.credentials:
            raise KMSAPIError(1000, "credential already exists")
        self._next_id += 1
        self.credentials[name] = CredentialInfo(
            credential_id=self._next_id, scope=scope, name=name, enable_encrypt=True, auth=auth
        )
        self.envelopes[name] = envelope
        self.created.append(name)
        if self.create_outcome_unknown:
            raise KMSRequestError("timeout after the request was accepted")
        return self._next_id

    def delete_credential(self, credential_id: int) -> None:
        self.deleted_ids.append(credential_id)
        self.credentials = {k: v for k, v in self.credentials.items() if v.credential_id != credential_id}


class FakeKube:
    """Kubernetes 替身：按 (apiVersion, kind, namespace, name) 保存对象，UID 在首次 apply 时分配"""

    def __init__(self):
        self.objects: dict[tuple[str, str, str | None, str], dict[str, Any]] = {}
        self.applied_kinds: list[str] = []
        self.fail_apply_with: Exception | None = None
        self.fail_delete_with: Exception | None = None
        self._seq = 0

    def apply(self, manifest):
        if self.fail_apply_with is not None:
            raise self.fail_apply_with
        meta = manifest["metadata"]
        key = (manifest["apiVersion"], manifest["kind"], meta.get("namespace"), meta["name"])
        self.applied_kinds.append(manifest["kind"])
        existing = self.objects.get(key)
        if existing is None:
            self._seq += 1
            uid = f"uid-{self._seq}"
        else:
            uid = existing["metadata"]["uid"]
        obj = copy.deepcopy(dict(manifest))
        obj["metadata"] = {**obj["metadata"], "uid": uid}
        if existing is not None and "status" in existing:
            obj["status"] = existing["status"]
        self.objects[key] = obj
        return uid

    def get(self, *, api_version, kind, name, namespace):
        return copy.deepcopy(self.objects.get((api_version, kind, namespace, name)))

    def delete(self, *, api_version, kind, name, namespace):
        if self.fail_delete_with is not None:
            raise self.fail_delete_with
        self.objects.pop((api_version, kind, namespace, name), None)
        # 模拟 ownerReference 级联删除目标 Secret
        if kind == "ExternalSecret":
            self.objects.pop(("v1", "Secret", namespace, name), None)

    def mark_synced(self, namespace: str, name: str) -> None:
        """模拟 ESO 同步成功：ExternalSecret 变为 Ready，并生成带 ownerReference 的目标 Secret"""
        es = self.objects[(ES_API_VERSION, "ExternalSecret", namespace, name)]
        es["status"] = {
            "conditions": [{"type": "Ready", "status": "True", "reason": "SecretSynced"}],
            "refreshTime": "2026-10-12T08:00:00Z",
        }
        self.objects[("v1", "Secret", namespace, name)] = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {
                "name": name,
                "namespace": namespace,
                "uid": "secret-uid-1",
                "ownerReferences": [{"kind": "ExternalSecret", "name": name, "uid": es["metadata"]["uid"]}],
            },
            "data": {"envelope": "ZW52", "privateKey": "cHJpdg=="},
        }


class SyncingKube(FakeKube):
    """apply ExternalSecret 后立即模拟 ESO 同步完成"""

    def apply(self, manifest):
        uid = super().apply(manifest)
        if manifest["kind"] == "ExternalSecret":
            self.mark_synced(manifest["metadata"]["namespace"], manifest["metadata"]["name"])
        return uid


@pytest.fixture()
def kms_cfg() -> KMSSaaSSettings:
    return KMSSaaSSettings(
        scope_id=15,
        scope_name="test-scope",
        openbao_server="https://openbao.example.com",
        kv_path="secret",
        k8s_auth_mount="kubernetes",
        mtls_secret_namespace="paas-system",
        mtls_secret_name="openbao-mtls-client",
        refresh_interval="1h",
        ready_timeout_seconds=300,
        ready_poll_interval_seconds=5,
    )


@pytest.fixture()
def _cluster(mocker):
    mocker.patch.object(EnvClusterService, "get_cluster_name", return_value=CLUSTER_NAME)


@pytest.fixture()
def kms() -> FakeKMS:
    return FakeKMS()


@pytest.fixture()
def kube() -> FakeKube:
    return FakeKube()


@pytest.fixture()
def version(bk_stag_env, wl_app, _cluster, kms_cfg) -> KMSConfigVersion:
    """一个已冻结、状态为 pending 的配置版本"""
    return create_kms_config_version(bk_stag_env, SENSITIVE_ENV, kms=FakeKMS(), kms_settings=kms_cfg)


@pytest.fixture()
def make_provisioner(kms, kube, kms_cfg):
    def maker(version: KMSConfigVersion, **kwargs) -> KMSSecretProvisioner:
        return KMSSecretProvisioner(version, kms=kms, kube=kube, kms_settings=kms_cfg, **kwargs)

    return maker


@pytest.mark.usefixtures("wl_app", "_cluster")
class TestCreateKMSConfigVersion:
    def test_stores_only_envelope(self, bk_stag_env, kms, kms_cfg):
        version = create_kms_config_version(bk_stag_env, SENSITIVE_ENV, kms=kms, kms_settings=kms_cfg)

        payload = json.loads(kms.plaintexts[0])
        assert payload["config_version_id"] == version.id
        assert payload["env"] == SENSITIVE_ENV

        row = KMSConfigVersion.objects.get(pk=version.id)
        assert row.status == KMSConfigVersionStatus.PENDING.value
        assert row.envelope == "envelope-1"
        stored = " ".join(str(getattr(row, f.attname)) for f in KMSConfigVersion._meta.concrete_fields)
        assert "s3cret-value-xyz" not in stored
        assert "tok-abc-123" not in stored

    def test_rejects_empty_sensitive_env(self, bk_stag_env, kms, kms_cfg):
        with pytest.raises(KMSValidationError):
            create_kms_config_version(bk_stag_env, {}, kms=kms, kms_settings=kms_cfg)

        assert KMSConfigVersion.objects.count() == 0


def test_load_kms_settings_reports_all_missing_required_settings():
    with (
        override_settings(KMS_SAAS_SCOPE_ID=0, KMS_SAAS_SCOPE_NAME="", KMS_OPENBAO_SERVER=""),
        pytest.raises(KMSConfigError) as exc_info,
    ):
        load_kms_settings()

    message = str(exc_info.value)
    assert "KMS_SAAS_SCOPE_ID" in message
    assert "KMS_SAAS_SCOPE_NAME" in message
    assert "KMS_OPENBAO_SERVER" in message


class TestKMSSecretProvisioner:
    def test_provision_creates_credential_and_resources(self, version, make_provisioner, kms, kube):
        make_provisioner(version).provision()

        version.refresh_from_db()
        assert version.status == KMSConfigVersionStatus.RESOURCES_APPLIED.value
        credential = kms.credentials[version.credential_name]
        assert version.credential_id == credential.credential_id
        # 凭证使用冻结时保存的信封，且只允许本环境的专用 SA 在本 namespace 中读取
        assert kms.envelopes[version.credential_name] == version.envelope
        assert credential.auth == ServiceAccountAuth(
            name_list=(version.service_account_name,), namespace_list=(version.namespace,)
        )

        # SA 必须先于 ExternalSecret 存在
        assert kube.applied_kinds == ["ServiceAccount", "ClusterSecretStore", "ExternalSecret"]
        store = kube.get(
            api_version=ES_API_VERSION, kind="ClusterSecretStore", name=version.resource_name, namespace=None
        )
        assert store["spec"]["provider"]["vault"]["auth"]["kubernetes"]["role"] == version.kms_role
        assert store["spec"]["conditions"] == [{"namespaces": [version.namespace]}]
        es = kube.get(
            api_version=ES_API_VERSION, kind="ExternalSecret", name=version.resource_name, namespace=version.namespace
        )
        assert es["spec"]["data"][0]["remoteRef"]["key"] == version.openbao_key
        assert version.external_secret_uid == es["metadata"]["uid"]

    def test_provision_is_idempotent(self, version, make_provisioner, kms):
        provisioner = make_provisioner(version)
        provisioner.provision()
        es_uid = version.external_secret_uid

        provisioner.provision()

        assert kms.created == [version.credential_name]
        assert version.external_secret_uid == es_uid

    def test_existing_matching_credential_is_adopted(self, version, make_provisioner, kms):
        provisioner = make_provisioner(version)
        provisioner.provision()
        # 模拟保存 credential_id 之前进程中断
        version.credential_id = None
        version.save()

        provisioner.ensure_credential()

        assert kms.created == [version.credential_name]
        assert version.credential_id == kms.credentials[version.credential_name].credential_id

    def test_unknown_create_outcome_is_reconciled_by_name(self, version, make_provisioner, kms):
        kms.create_outcome_unknown = True

        make_provisioner(version).ensure_credential()

        version.refresh_from_db()
        assert kms.created == [version.credential_name]
        assert version.credential_id == kms.credentials[version.credential_name].credential_id
        assert version.status == KMSConfigVersionStatus.CREDENTIAL_CREATED.value

    def test_mismatched_existing_credential_is_rejected(self, version, make_provisioner, kms):
        kms.credentials[version.credential_name] = CredentialInfo(
            credential_id=7,
            scope=KMSScope(scope_id=15),
            name=version.credential_name,
            enable_encrypt=True,
            auth=ServiceAccountAuth(name_list=("other-sa",), namespace_list=("other-ns",)),
        )

        with pytest.raises(KMSCredentialMismatchError):
            make_provisioner(version).ensure_credential()

        version.refresh_from_db()
        assert version.credential_id is None
        assert version.error_reason == "KMSCredentialMismatchError"

    def test_kms_api_error_is_recorded_without_advancing(self, version, make_provisioner, kms):
        kms.fail_create_with = KMSAPIError(1010, "server busy")

        with pytest.raises(KMSAPIError):
            make_provisioner(version).ensure_credential()

        version.refresh_from_db()
        assert version.status == KMSConfigVersionStatus.PENDING.value
        assert version.error_reason == "kms_api_error_1010"

    def test_kube_api_error_is_recorded_without_advancing(self, version, make_provisioner, kube):
        kube.fail_apply_with = ApiException(status=403, reason="Forbidden")

        with pytest.raises(ApiException):
            make_provisioner(version).provision()

        version.refresh_from_db()
        assert version.status == KMSConfigVersionStatus.CREDENTIAL_CREATED.value
        assert version.error_reason == "kube_api_error_403"

    def test_wait_ready_polls_until_secret_is_synced(self, version, make_provisioner, kube):
        # 第一次检查未就绪，sleep 之后 ESO 完成同步
        provisioner = make_provisioner(
            version, sleep=lambda _: kube.mark_synced(version.namespace, version.resource_name)
        )
        provisioner.provision()

        provisioner.wait_ready(timeout=60, poll_interval=0)

        version.refresh_from_db()
        assert version.status == KMSConfigVersionStatus.READY.value

    def test_wait_ready_timeout_records_last_reason(self, version, make_provisioner):
        provisioner = make_provisioner(version)
        provisioner.provision()

        with pytest.raises(KMSSecretNotReadyError):
            provisioner.wait_ready(timeout=0, poll_interval=0)

        version.refresh_from_db()
        assert version.error_reason == "external_secret_not_ready:unknown"
        assert version.status == KMSConfigVersionStatus.RESOURCES_APPLIED.value

    def test_reapply_never_moves_status_backwards(self, version, make_provisioner, kube):
        provisioner = make_provisioner(
            version, sleep=lambda _: kube.mark_synced(version.namespace, version.resource_name)
        )
        provisioner.provision()
        provisioner.wait_ready(timeout=60, poll_interval=0)

        provisioner.apply_resources()

        version.refresh_from_db()
        assert version.status == KMSConfigVersionStatus.READY.value


@pytest.mark.usefixtures("wl_app", "_cluster")
class TestProvisionKMSSecret:
    def test_provisions_and_links_deployment(self, bk_stag_env, bk_deployment, kms, kms_cfg):
        mount = provision_kms_secret(
            bk_stag_env, bk_deployment, SENSITIVE_ENV, kms=kms, kube=SyncingKube(), kms_settings=kms_cfg
        )

        bk_deployment.refresh_from_db()
        version = bk_deployment.kms_config_version
        assert version is not None
        assert version.status == KMSConfigVersionStatus.READY.value
        # 应用端 SDK 从 /etc/kms/envelope 与 /etc/kms/privateKey 读取
        assert mount == SecretFileMount(
            volume_name="kms-secret",
            secret_name=version.resource_name,
            mount_dir="/etc/kms",
            sub_paths=("envelope", "privateKey"),
        )

    def test_unchanged_values_reuse_ready_version(self, bk_stag_env, bk_deployment, bk_module, kms, kms_cfg):
        kube = SyncingKube()
        first = provision_kms_secret(
            bk_stag_env, bk_deployment, SENSITIVE_ENV, kms=kms, kube=kube, kms_settings=kms_cfg
        )
        # 模拟 Secret 被误删：复用时重新提交资源并等待同步
        kube.objects.clear()

        next_deployment = create_fake_deployment(bk_module, app_environment="stag")
        second = provision_kms_secret(
            bk_stag_env, next_deployment, dict(SENSITIVE_ENV), kms=kms, kube=kube, kms_settings=kms_cfg
        )

        assert second == first
        assert KMSConfigVersion.objects.count() == 1
        assert len(kms.created) == 1
        assert kube.get(
            api_version="v1", kind="Secret", name=first.secret_name, namespace=bk_stag_env.wl_app.namespace
        )

    def test_failed_version_is_not_reused(self, bk_stag_env, bk_deployment, kms, kms_cfg):
        kube = SyncingKube()
        first = provision_kms_secret(
            bk_stag_env, bk_deployment, SENSITIVE_ENV, kms=kms, kube=kube, kms_settings=kms_cfg
        )
        # 模拟复用时远端资源已损坏，等待就绪失败
        KMSConfigVersion.objects.update(error_reason="external_secret_not_ready:SecretSyncedError")

        second = provision_kms_secret(
            bk_stag_env, bk_deployment, SENSITIVE_ENV, kms=kms, kube=kube, kms_settings=kms_cfg
        )

        assert second.secret_name != first.secret_name
        assert KMSConfigVersion.objects.count() == 2

    def test_changed_values_create_new_version(self, bk_stag_env, bk_deployment, kms, kms_cfg):
        kube = SyncingKube()
        first = provision_kms_secret(
            bk_stag_env, bk_deployment, SENSITIVE_ENV, kms=kms, kube=kube, kms_settings=kms_cfg
        )

        second = provision_kms_secret(
            bk_stag_env,
            bk_deployment,
            {**SENSITIVE_ENV, "DB_PASSWORD": "rotated"},
            kms=kms,
            kube=kube,
            kms_settings=kms_cfg,
        )

        assert second.secret_name != first.secret_name
        assert KMSConfigVersion.objects.count() == 2

    def test_kms_failure_keeps_deployment_linked(self, bk_stag_env, bk_deployment, kms, kms_cfg):
        kube = SyncingKube()
        kms.fail_create_with = KMSAPIError(1000, "boom")

        with pytest.raises(KMSAPIError):
            provision_kms_secret(bk_stag_env, bk_deployment, SENSITIVE_ENV, kms=kms, kube=kube, kms_settings=kms_cfg)

        bk_deployment.refresh_from_db()
        version = bk_deployment.kms_config_version
        assert version is not None
        assert version.error_reason == "kms_api_error_1000"
        assert kube.applied_kinds == []


@pytest.mark.usefixtures("wl_app", "_cluster")
class TestRecycleKMSConfigVersions:
    @pytest.fixture()
    def kube(self) -> SyncingKube:
        return SyncingKube()

    @pytest.fixture()
    def factories(self, kms, kube):
        return {"kms_factory": lambda tenant_id: kms, "kube_factory": lambda cluster_name: kube}

    @pytest.fixture()
    def deploy(self, bk_stag_env, bk_module, kms, kube, kms_cfg):
        """创建一次部署并为其准备 KMS 配置版本；每次使用不同的敏感值，以生成新版本"""

        def _deploy(status: JobStatus = JobStatus.SUCCESSFUL) -> Deployment:
            deployment = create_fake_deployment(bk_module, app_environment="stag")
            values = {**SENSITIVE_ENV, "DB_PASSWORD": f"pwd-{deployment.pk}"}
            provision_kms_secret(bk_stag_env, deployment, values, kms=kms, kube=kube, kms_settings=kms_cfg)
            Deployment.objects.filter(pk=deployment.pk).update(status=status.value)
            deployment.refresh_from_db()
            return deployment

        return _deploy

    def _es_exists(self, kube, version: KMSConfigVersion) -> bool:
        return bool(
            kube.get(
                api_version=ES_API_VERSION,
                kind="ExternalSecret",
                name=version.resource_name,
                namespace=version.namespace,
            )
        )

    def test_keeps_latest_two_successful_deployments(self, deploy, kms, kube, factories):
        first, second, third = deploy(), deploy(), deploy()
        stale = first.kms_config_version

        recycle_stale_kms_config_versions(third, **factories)

        assert set(KMSConfigVersion.objects.values_list("pk", flat=True)) == {
            second.kms_config_version_id,
            third.kms_config_version_id,
        }
        assert not self._es_exists(kube, stale)
        assert not kube.get(
            api_version=ES_API_VERSION, kind="ClusterSecretStore", name=stale.resource_name, namespace=None
        )
        assert kms.deleted_ids == [stale.credential_id]
        assert self._es_exists(kube, second.kms_config_version)

    def test_skips_versions_of_unfinished_or_newer_deployments(self, deploy, factories):
        pending = deploy(status=JobStatus.PENDING)
        failed = deploy(status=JobStatus.FAILED)
        deploy()
        current = deploy()
        newer = deploy(status=JobStatus.PENDING)

        recycle_stale_kms_config_versions(current, **factories)

        remaining = set(KMSConfigVersion.objects.values_list("pk", flat=True))
        assert pending.kms_config_version_id in remaining
        assert failed.kms_config_version_id not in remaining
        assert newer.kms_config_version_id in remaining

    def test_failed_recycling_keeps_record_and_blocks_reuse(self, deploy, kube, factories):
        first, _, third = deploy(), deploy(), deploy()
        kube.fail_delete_with = ApiException(status=500, reason="boom")

        recycle_stale_kms_config_versions(third, **factories)

        stale = KMSConfigVersion.objects.get(pk=first.kms_config_version_id)
        assert stale.error_reason == RECYCLING_REASON

    def test_module_deletion_recycles_all_versions(self, bk_stag_env, deploy, kms, factories):
        deploy(), deploy(status=JobStatus.PENDING)

        recycle_module_env_kms_config_versions(bk_stag_env, **factories)

        assert KMSConfigVersion.objects.count() == 0
        assert len(kms.deleted_ids) == 2
