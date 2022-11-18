# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
import logging
import time
from pathlib import Path, PosixPath
from typing import List

from attrs import define
from django.conf import settings
from django.utils.translation import get_language
from packaging.version import InvalidVersion, Version, parse

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
            # 非文件或者非 md 结尾的文件忽略
            if not file.is_file():
                logger.error(f'ignore changelog file {file.name}')
                continue

            try:
                detail = self._parse_log(file)
            except InvalidChangelogError as e:
                logger.error(f'invalid changelog file name {file.name}: {e}')
            else:
                logs.append(detail)

        # 按照版本号语义降序排序
        logs = sorted(logs, key=lambda l: Version(l.version), reverse=True)
        return logs

    def _parse_log(self, file: PosixPath) -> LogDetail:
        """解析日志文件, 获取版本, 日期以及日志内容

        :raise InvalidChangelogError. 表示解析到的日志文件无效. 有效的文件名格式如 v1.1.1_2022-11-17.md
        """
        if file.suffix != '.md':
            raise InvalidChangelogError('file name not end with .md')

        version, _, date = file.stem.partition('_')

        try:
            parse(version)
            time.strptime(date, '%Y-%m-%d')
        except (TypeError, ValueError, InvalidVersion):
            raise InvalidChangelogError('file name contains invalid version or date time')

        return LogDetail(version=version, date=date, content=file.read_text())
