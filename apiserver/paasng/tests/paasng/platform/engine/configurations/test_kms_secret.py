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

from paas_wl.bk_app.cnative.specs.crd import bk_app as crd
from paas_wl.bk_app.cnative.specs.crd.metadata import ObjectMetadata
from paas_wl.bk_app.processes.entities import SecretFileMount
from paas_wl.infras.cluster.shim import EnvClusterService
from paasng.infras.kms.client import CredentialInfo, KMSClient, KMSScope, ServiceAccountAuth
from paasng.infras.kms.exceptions import (
    KMSAPIError,
    KMSConfigError,
    KMSCredentialMismatchError,
    KMSRequestError,
    KMSSecretNotReadyError,
    KMSValidationError,
)
from paasng.platform.engine.configurations.env_var.encryption import (
    CIPHER_PREFIX,
    ENCRYPTED_KEYS_ENV_NAME,
    SECRET_KEY_ENV_VAR_NAME,
)
from paasng.platform.engine.configurations.kms_secret import (
    KMSSaaSSettings,
    KMSSecretProvisioner,
    add_kms_secret_mount,
    collect_kms_managed_keys,
    create_kms_config_version,
    load_kms_settings,
    provision_kms_secret,
    strip_kms_managed_env_vars,
)
from paasng.platform.engine.constants import KMSConfigVersionStatus
from paasng.platform.engine.exceptions import DeployShouldAbortError
from paasng.platform.engine.models import KMSConfigVersion

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


class FakeKube:
    """Kubernetes 替身：按 (apiVersion, kind, namespace, name) 保存对象，UID 在首次 apply 时分配"""

    def __init__(self):
        self.objects: dict[tuple[str, str, str | None, str], dict[str, Any]] = {}
        self.applied_kinds: list[str] = []
        self.fail_apply_with: Exception | None = None
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
        es = kube.get(
            api_version=ES_API_VERSION, kind="ExternalSecret", name=version.resource_name, namespace=version.namespace
        )
        assert es["spec"]["data"][0]["remoteRef"]["key"] == version.openbao_key
        assert version.cluster_secret_store_uid == store["metadata"]["uid"]
        assert version.external_secret_uid == es["metadata"]["uid"]

    def test_provision_is_idempotent(self, version, make_provisioner, kms):
        provisioner = make_provisioner(version)
        provisioner.provision()
        uids = (version.cluster_secret_store_uid, version.external_secret_uid)

        provisioner.provision()

        assert kms.created == [version.credential_name]
        assert (version.cluster_secret_store_uid, version.external_secret_uid) == uids

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
        assert version.secret_uid == "secret-uid-1"

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


def test_collect_kms_managed_keys_excludes_unmanaged_builtin_keys(bk_stag_env, mocker):
    mocker.patch(
        "paasng.platform.engine.configurations.kms_secret.collect_sensitive_keys",
        return_value={"DB_PASSWORD", "BKPAAS_APP_SECRET"},
    )

    assert collect_kms_managed_keys(bk_stag_env) == {"DB_PASSWORD"}


def _make_bkapp(
    env_vars: list[tuple[str, str]] | None = None,
    overlay_vars: list[tuple[str, str, str]] | None = None,
    mounts: list[crd.Mount] | None = None,
    overlay_mounts: list[crd.MountOverlay] | None = None,
) -> crd.BkAppResource:
    """构造只包含配置相关字段的 BkApp。overlay_vars 的每一项为 (envName, name, value)"""
    overlay = None
    if overlay_vars or overlay_mounts:
        overlay = crd.EnvOverlay(
            envVariables=[crd.EnvVarOverlay(envName=e, name=n, value=v) for e, n, v in overlay_vars or []] or None,
            mounts=overlay_mounts,
        )
    return crd.BkAppResource(
        metadata=ObjectMetadata(name="app"),
        spec=crd.BkAppSpec(
            configuration=crd.BkAppConfiguration(env=[crd.EnvVar(name=n, value=v) for n, v in env_vars or []]),
            mounts=mounts,
            envOverlay=overlay,
        ),
    )


def _overlay_var_names(bkapp: crd.BkAppResource) -> list[tuple[str, str]]:
    assert bkapp.spec.envOverlay is not None
    return [(var.envName, var.name) for var in bkapp.spec.envOverlay.envVariables or []]


class TestStripKMSManagedEnvVars:
    def test_removes_managed_keys_from_default_and_overlays(self):
        bkapp = _make_bkapp(
            env_vars=[("DB_PASSWORD", "s3cret"), ("PLAIN", "1")],
            overlay_vars=[
                ("stag", "DB_PASSWORD", "s3cret-stag"),
                ("prod", "DB_PASSWORD", f"{CIPHER_PREFIX}abc"),
                ("prod", "TOKEN", "tok"),
            ],
        )

        strip_kms_managed_env_vars(bkapp, "stag", {"stag": frozenset({"DB_PASSWORD"}), "prod": frozenset({"TOKEN"})})

        assert [var.name for var in bkapp.spec.configuration.env] == ["PLAIN"]
        # 覆盖项按各自环境的托管键过滤
        assert _overlay_var_names(bkapp) == [("prod", "DB_PASSWORD")]

    def test_encryption_metadata_removed_when_no_ciphertext_left(self):
        bkapp = _make_bkapp(
            overlay_vars=[
                ("stag", "DB_PASSWORD", f"{CIPHER_PREFIX}abc"),
                ("stag", SECRET_KEY_ENV_VAR_NAME, "key"),
                ("stag", ENCRYPTED_KEYS_ENV_NAME, "DB_PASSWORD"),
            ],
        )

        strip_kms_managed_env_vars(bkapp, "stag", {"stag": frozenset({"DB_PASSWORD"})})

        assert _overlay_var_names(bkapp) == []

    def test_encryption_metadata_kept_when_other_ciphertext_remains(self):
        bkapp = _make_bkapp(
            overlay_vars=[
                ("stag", "DB_PASSWORD", f"{CIPHER_PREFIX}abc"),
                ("prod", "TOKEN", f"{CIPHER_PREFIX}def"),
                ("prod", SECRET_KEY_ENV_VAR_NAME, "key"),
                ("prod", ENCRYPTED_KEYS_ENV_NAME, "TOKEN"),
            ],
        )

        strip_kms_managed_env_vars(bkapp, "stag", {"stag": frozenset({"DB_PASSWORD"})})

        assert _overlay_var_names(bkapp) == [
            ("prod", "TOKEN"),
            ("prod", SECRET_KEY_ENV_VAR_NAME),
            ("prod", ENCRYPTED_KEYS_ENV_NAME),
        ]


KMS_MOUNT = SecretFileMount(
    volume_name="kms-secret", secret_name="kms-res-1", mount_dir="/etc/kms", sub_paths=("envelope", "privateKey")
)


def _user_mount(name: str, mount_path: str, env_name: str | None = None) -> crd.Mount | crd.MountOverlay:
    source = crd.VolumeSource(secret=crd.SecretSource(name="user"))
    if env_name:
        return crd.MountOverlay(envName=env_name, name=name, mountPath=mount_path, source=source)
    return crd.Mount(name=name, mountPath=mount_path, source=source)


class TestAddKMSSecretMount:
    def test_appends_overlay_mount_for_env(self):
        bkapp = _make_bkapp()

        add_kms_secret_mount(bkapp, "stag", KMS_MOUNT)

        assert bkapp.to_deployable()["spec"]["envOverlay"]["mounts"] == [
            {
                "envName": "stag",
                "name": "kms-secret",
                "mountPath": "/etc/kms",
                "source": {"secret": {"name": "kms-res-1"}},
                "subPaths": ["envelope", "privateKey"],
            }
        ]

    @pytest.mark.parametrize(
        ("user_mount", "conflict"),
        [
            (_user_mount("kms-secret", "/data"), True),
            (_user_mount("data", "/etc/kms"), True),
            (_user_mount("data", "/etc/kms/extra"), True),
            (_user_mount("data", "/etc/kms-other"), False),
            (_user_mount("data", "/etc/kms", env_name="stag"), True),
            (_user_mount("kms-secret", "/etc/kms", env_name="prod"), False),
        ],
    )
    def test_conflicts_with_user_mounts(self, user_mount, conflict):
        if isinstance(user_mount, crd.MountOverlay):
            bkapp = _make_bkapp(overlay_mounts=[user_mount])
        else:
            bkapp = _make_bkapp(mounts=[user_mount])

        if conflict:
            with pytest.raises(DeployShouldAbortError):
                add_kms_secret_mount(bkapp, "stag", KMS_MOUNT)
        else:
            add_kms_secret_mount(bkapp, "stag", KMS_MOUNT)
