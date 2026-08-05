# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

"""清理超过保留时长的 bkrepo 归档产物。"""

import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from django.utils import timezone

from paasng.platform.agent_sandbox.models import VolumeArtifact
from paasng.utils.blobstore import make_blob_store

DEFAULT_CLEANUP_CONCURRENCY = 4


def expired_artifact_queryset(expired_before: datetime, app_code: str | None = None):
    """Return artifacts archived before ``expired_before``."""
    queryset = (
        VolumeArtifact.objects.filter(archived_at__lte=expired_before)
        .select_related("volume__application")
        .order_by("archived_at", "uuid")
    )
    if app_code:
        queryset = queryset.filter(volume__application__code=app_code)
    return queryset


@dataclass
class _DeleteResult:
    success: bool
    artifact: VolumeArtifact
    error: Exception | None = None


def _delete_expired_artifact(artifact_uuid: uuid.UUID, expired_before: datetime) -> _DeleteResult | None:
    """Delete one bkrepo object and its mapping record.

    The mapping record is removed only after bkrepo deletion succeeds so a
    failed cleanup remains eligible for the next scheduled run.
    """
    close_old_connections()
    try:
        artifact = VolumeArtifact.objects.select_related("volume__application").get(
            uuid=artifact_uuid, archived_at__lte=expired_before
        )
    except VolumeArtifact.DoesNotExist:
        return None

    try:
        store = make_blob_store(settings.AGENT_SANDBOX_ARTIFACT_BUCKET)
        store.delete_file(artifact.bkrepo_key)
        artifact.delete()
    except Exception as exc:  # noqa: BLE001
        return _DeleteResult(success=False, artifact=artifact, error=exc)
    return _DeleteResult(success=True, artifact=artifact)


class Command(BaseCommand):
    help = "清理超过保留时长的 bkrepo 归档产物"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", dest="dry_run", action="store_true", help="仅显示将被清理的归档产物，不实际执行删除操作"
        )
        parser.add_argument(
            "--concurrency",
            dest="concurrency",
            type=int,
            default=DEFAULT_CLEANUP_CONCURRENCY,
            help=f"并发删除的归档产物数量，默认 {DEFAULT_CLEANUP_CONCURRENCY}",
        )
        parser.add_argument("--app-code", dest="app_code", help="仅清理指定应用的归档产物")
        parser.add_argument(
            "--expired-hours",
            dest="expired_hours",
            type=int,
            required=True,
            help="删除归档时间早于指定小时数的产物",
        )

    def handle(self, dry_run, concurrency, app_code, expired_hours, *args, **options):
        if concurrency < 1:
            self.stderr.write(self.style.ERROR("concurrency 必须大于 0"))
            return
        if expired_hours < 0:
            self.stderr.write(self.style.ERROR("expired-hours 不能小于 0"))
            return

        expired_before = timezone.now() - timedelta(hours=expired_hours)
        artifacts = expired_artifact_queryset(expired_before, app_code)
        total = artifacts.count()
        app_filter = f"（应用: {app_code}）" if app_code else ""
        self.stdout.write(f"共找到 {total} 个已过期归档产物待清理{app_filter}")

        if total == 0:
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("dry-run 模式：仅显示，不实际删除"))
            for artifact in artifacts:
                self.stdout.write(
                    f"uuid={artifact.uuid} volume_id={artifact.volume.uuid} "
                    f"app_code={artifact.volume.application.code} key={artifact.bkrepo_key}"
                )
            return

        artifact_uuids = list(artifacts.values_list("uuid", flat=True))
        deleted_count = 0
        failed_count = 0
        workers = min(concurrency, len(artifact_uuids))
        self.stdout.write(f"并发数: {workers}")

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(_delete_expired_artifact, artifact_uuid, expired_before)
                for artifact_uuid in artifact_uuids
            ]
            for future in as_completed(futures):
                result = future.result()
                if result is None:
                    continue

                artifact = result.artifact
                if result.success:
                    deleted_count += 1
                    self.stdout.write(
                        f"已删除 {deleted_count}/{total} uuid={artifact.uuid} "
                        f"volume_id={artifact.volume.uuid} key={artifact.bkrepo_key}"
                    )
                else:
                    failed_count += 1
                    self.stderr.write(
                        self.style.ERROR(
                            f"删除失败 uuid={artifact.uuid} volume_id={artifact.volume.uuid} "
                            f"key={artifact.bkrepo_key}: {result.error}"
                        )
                    )

        self.stdout.write(f"清理完成: 删除 {deleted_count} 个, 失败 {failed_count} 个")
