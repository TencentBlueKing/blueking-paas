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
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Pattern, Set, Tuple

from django.conf import settings
from django.core.management.base import BaseCommand

from paas_wl.bk_app.applications.models.build import Build
from paas_wl.utils.blobstore import BKGenericRepo, S3Store, make_blob_store

logger = logging.getLogger(__name__)
_store = None


@dataclass
class AppBucket:
    builds: List[Build] = field(default_factory=list)
    caches: Set[str] = field(default_factory=set)

    def append(self, build: Build):
        revision_path = build.slug_path
        if revision_path.endswith("/push"):
            revision_path = revision_path[:-4]
        if revision_path not in self.caches:
            self.caches.add(revision_path)
            self.builds.append(build)


class Command(BaseCommand):
    help = 'A batch to delete expired S3 slug/tar package'

    def add_arguments(self, parser):
        parser.add_argument(
            "-p",
            "--match-pattern",
            dest="match_pattern",
            default=None,
            type=str,
            help="If provide this argument, will only remove those object that match the rule.",
        )
        parser.add_argument(
            "-max",
            "--max-reserved-num-per-env",
            dest="max_reserved_num_per_env",
            type=int,
            default=5,
            help="How many S3 slug package will be reserved in each environ, default is 5.",
        )
        parser.add_argument(
            "-d",
            "--dry-run",
            dest="dry_run",
            action="store_true",
            help="Just show what S3 slug package would be delete; don't actually delete them.",
        )

    def handle(self, match_pattern, max_reserved_num_per_env, dry_run, *args, **options):
        # Build 对象存储构建后的 slug 包, 倒序查询
        build_query_set = Build.objects.exclude(slug_path=None).select_related("app").order_by("-created")
        bucket_dict: Dict[str, AppBucket] = defaultdict(AppBucket)
        deleted_count = 0
        deleted_size = 0

        if match_pattern:
            match_pattern = re.compile(match_pattern)

        for build in build_query_set:
            # 顺序入队
            bucket_dict[str(build.app.name)].append(build)

        for _, bucket in bucket_dict.items():
            # 按创建时间倒序查询, 并顺序入队后, 目前队列则是按时间顺序排列,
            # 因此这里只需要保留前 max_reserved_num_per_env 个.
            for build in bucket.builds[max_reserved_num_per_env:]:
                result = delete_from_blob_store(build, dry_run=dry_run, pattern=match_pattern)

                deleted_count += result[0]
                deleted_size += result[1]

        self.stdout.write(
            self.style.SUCCESS(f'\nSuccessfully to delete {deleted_count} slug package, total {deleted_size} bytes')
        )


def delete_from_blob_store(build: Build, dry_run: bool = True, pattern: Optional[Pattern] = None) -> Tuple[int, int]:
    """从 blob_store 删除构建产物"""
    if build.artifact_deleted:
        return 0, 0

    store = get_store()
    logger.info("正在删除构建产物 %s", build)

    # some path look like '{region}/home/{engine_app_name}:{branch}:{revision}/' ,其涵盖了 slug_path, source_tar_path 两者
    # revision_path 下主要有 3 个文件需要被清理, push/Procfile, push/slug.tgz, /tar
    revision_path = build.slug_path
    if revision_path.endswith("/push"):
        revision_path = revision_path[:-4]

    targets = ["push/Procfile", "push/slug.tgz", "tar"]
    deleted_count = 0
    deleted_size = 0

    for target in targets:
        key = revision_path + target
        if pattern and not pattern.match(key):
            logger.info("文件 %s 不符合删除规则 %s, 跳过删除.", key, pattern)
            continue

        try:
            file_size = parse_file_size(store.get_file_metadata(key))
            logger.info("删除文件 %s, 将释放 %s bytes 空间", key, file_size)
            if not dry_run:
                store.delete_file(key)
            deleted_count += 1
            deleted_size += file_size
        except Exception:
            logger.exception("删除资源 %s 失败", key)

    if not dry_run:
        build.artifact_deleted = True
        build.save(update_fields=["artifact_deleted", "updated"])
    return deleted_count, deleted_size


def get_store():
    global _store
    if _store is None:
        _store = make_blob_store(settings.BLOBSTORE_BUCKET_APP_SOURCE)
    return _store


def parse_file_size(metadata: Dict) -> int:
    """从 metadata 解析出文件大小"""
    store = get_store()
    if isinstance(store, S3Store):
        return int(metadata["ContentLength"])
    elif isinstance(store, BKGenericRepo):
        return int(metadata["Content-Length"])
    raise NotImplementedError("不支持的仓库类型, 无法获取到文件大小.")
