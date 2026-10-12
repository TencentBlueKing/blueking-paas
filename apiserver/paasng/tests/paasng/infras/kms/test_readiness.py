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

from typing import Any

import pytest

from paasng.infras.kms.readiness import evaluate_secret_readiness

ES_NAME = "kms-default-demo-web-prod-0b1f4c2e8d3a4f6b9c1d2e3f4a5b6c7d"
ES_UID = "es-uid-1"
SECRET_UID = "secret-uid-1"


def _external_secret(
    *,
    uid: str = ES_UID,
    condition: dict[str, Any] | None = None,
    refresh_time: str | None = "2026-10-12T08:00:00Z",
    with_status: bool = True,
) -> dict[str, Any]:
    obj: dict[str, Any] = {"metadata": {"name": ES_NAME, "namespace": "bkapp-demo-prod", "uid": uid}}
    if not with_status:
        return obj
    status: dict[str, Any] = {
        "conditions": [condition or {"type": "Ready", "status": "True", "reason": "SecretSynced"}],
    }
    if refresh_time is not None:
        status["refreshTime"] = refresh_time
    obj["status"] = status
    return obj


def _secret(*, owner_uid: str = ES_UID, data: dict[str, str] | None = None, uid: str = SECRET_UID) -> dict[str, Any]:
    return {
        "metadata": {
            "name": ES_NAME,
            "namespace": "bkapp-demo-prod",
            "uid": uid,
            "ownerReferences": [
                {
                    "apiVersion": "external-secrets.io/v1beta1",
                    "kind": "ExternalSecret",
                    "name": ES_NAME,
                    "uid": owner_uid,
                }
            ],
        },
        "data": data if data is not None else {"envelope": "ZW52", "privateKey": "cHJpdg=="},
    }


class TestEvaluateSecretReadiness:
    def test_ready_when_all_conditions_hold(self):
        result = evaluate_secret_readiness(
            external_secret=_external_secret(),
            secret=_secret(),
            expected_external_secret_uid=ES_UID,
        )

        assert result.ready is True
        assert result.reason == "ready"
        assert result.secret_uid == SECRET_UID

    def test_external_secret_missing(self):
        result = evaluate_secret_readiness(external_secret=None, secret=None, expected_external_secret_uid=ES_UID)

        assert result.ready is False
        assert result.reason == "external_secret_missing"

    @pytest.mark.parametrize("expected_uid", ["", "other-uid"])
    def test_external_secret_uid_mismatch(self, expected_uid):
        result = evaluate_secret_readiness(
            external_secret=_external_secret(),
            secret=_secret(),
            expected_external_secret_uid=expected_uid,
        )

        assert result.ready is False
        assert result.reason == "external_secret_uid_mismatch"

    def test_external_secret_without_status_is_not_ready(self):
        result = evaluate_secret_readiness(
            external_secret=_external_secret(with_status=False),
            secret=_secret(),
            expected_external_secret_uid=ES_UID,
        )

        assert result.ready is False
        assert result.reason == "external_secret_not_ready:unknown"

    def test_ready_condition_false_uses_condition_reason_only(self):
        # message 可能包含 OpenBao 返回的细节，不能进入判定结果
        condition = {"type": "Ready", "status": "False", "reason": "SecretSyncedError", "message": "token=abc123"}
        result = evaluate_secret_readiness(
            external_secret=_external_secret(condition=condition),
            secret=_secret(),
            expected_external_secret_uid=ES_UID,
        )

        assert result.ready is False
        assert result.reason == "external_secret_not_ready:SecretSyncedError"
        assert "abc123" not in result.reason

    def test_external_secret_not_refreshed(self):
        result = evaluate_secret_readiness(
            external_secret=_external_secret(refresh_time=None),
            secret=_secret(),
            expected_external_secret_uid=ES_UID,
        )

        assert result.ready is False
        assert result.reason == "external_secret_not_refreshed"

    def test_secret_missing(self):
        result = evaluate_secret_readiness(
            external_secret=_external_secret(),
            secret=None,
            expected_external_secret_uid=ES_UID,
        )

        assert result.ready is False
        assert result.reason == "secret_missing"

    def test_secret_owned_by_another_external_secret(self):
        result = evaluate_secret_readiness(
            external_secret=_external_secret(),
            secret=_secret(owner_uid="someone-else"),
            expected_external_secret_uid=ES_UID,
        )

        assert result.ready is False
        assert result.reason == "secret_owner_mismatch"

    def test_secret_without_owner_reference(self):
        secret = _secret()
        secret["metadata"].pop("ownerReferences")

        result = evaluate_secret_readiness(
            external_secret=_external_secret(),
            secret=secret,
            expected_external_secret_uid=ES_UID,
        )

        assert result.ready is False
        assert result.reason == "secret_owner_mismatch"

    @pytest.mark.parametrize(
        "data",
        [
            {"envelope": "ZW52"},
            {"privateKey": "cHJpdg=="},
            {"envelope": "", "privateKey": "cHJpdg=="},
            {},
        ],
    )
    def test_secret_data_incomplete(self, data):
        result = evaluate_secret_readiness(
            external_secret=_external_secret(),
            secret=_secret(data=data),
            expected_external_secret_uid=ES_UID,
        )

        assert result.ready is False
        assert result.reason == "secret_data_missing"

    def test_secret_uid_missing(self):
        secret = _secret(uid="")

        result = evaluate_secret_readiness(
            external_secret=_external_secret(),
            secret=secret,
            expected_external_secret_uid=ES_UID,
        )

        assert result.ready is False
        assert result.reason == "secret_uid_missing"
