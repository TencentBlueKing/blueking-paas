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
import time
from functools import cmp_to_key
from pathlib import Path, PosixPath
from typing import List

from attrs import define
from django.conf import settings
from django.utils.translation import get_language
from semver import VersionInfo, compare

from .exceptions import InvalidChangelogError

logger = logging.getLogger(__name__)


@define
class LogDetail:
    version: str
    date: str
    content: str


class Changelog:
    """
    变更(版本)日志

    :param log_path: 版本日志存放目录. 目录下包含语言子目录, 如 /xxx/changelog/zh-cn
    """

    def __init__(self, log_path: str = settings.CHANGELOG_PATH):
        self.log_path = Path(log_path) / get_language()

    def list_logs(self) -> List[LogDetail]:
        """查询所有日志. 按照版本号语义降序排序"""
        if not self.log_path.is_dir():
            return []

        logs = []
        for file in self.log_path.iterdir():
            try:
                detail = self._parse_log(file)
            except InvalidChangelogError as e:
                logger.error(f'invalid changelog file {file.name}: {e}')
            else:
                logs.append(detail)

        # 按照版本号语义降序排序
        logs = sorted(logs, key=cmp_to_key(_compare_by_semver), reverse=True)
        return logs

    def _parse_log(self, file: PosixPath) -> LogDetail:
        """解析日志文件, 获取版本, 日期以及日志内容

        :raises 解析到的日志文件无效时, 抛出 InvalidChangelogError 异常. 有效的文件名格式如 V1.1.1_2022-11-17.md
        """
        if not file.is_file():
            raise InvalidChangelogError('not a file')

        if file.suffix != '.md':
            raise InvalidChangelogError('file name does not ends with .md')

        if not file.name.startswith('V'):
            raise InvalidChangelogError('file name must starts with letter V')

        version, _, date = file.stem.partition('_')

        try:
            # 去除版本号中的前缀 V 后校验语义版本
            VersionInfo.parse(version[1:])
            time.strptime(date, '%Y-%m-%d')
        except (TypeError, ValueError):
            raise InvalidChangelogError('file name contains invalid version or date time')

        return LogDetail(version=version, date=date, content=file.read_text())


def _compare_by_semver(x: LogDetail, y: LogDetail):
    """通过语义版本号比较大小"""
    # 去除版本号中的前缀 V
    return compare(x.version[1:], y.version[1:])
