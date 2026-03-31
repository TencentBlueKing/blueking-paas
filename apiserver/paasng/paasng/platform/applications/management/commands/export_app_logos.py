# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
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


"""批量导出应用 logo

Usage:
    python manage.py export_app_logos \
      --input-file /path/to/apps.txt \
      --logo-dir /path/to/logos
      --mapping-file /path/to/mapping.txt

输入文件格式(每行一条):
    {app_code} {tenant_id}

输出映射文件格式(每行一条):
    {app_code} {tenant_id} {logo_filename}
"""

from pathlib import Path

from bkstorages.backends.bkrepo import RequestError
from django.core.management.base import BaseCommand

from paasng.platform.applications.models import Application


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--input-file",
            dest="input_file",
            required=True,
            type=str,
            help="输入文件路径, 每行一条, 格式: {app_code} {tenant_id}",
        )
        parser.add_argument(
            "--logo-dir", dest="logo_dir", required=True, type=str, help="logo 文件下载路径, 不存在时自动创建"
        )
        parser.add_argument(
            "--mapping-file",
            dest="mapping_file",
            required=True,
            type=str,
            help="输出映射文件路径, 每行一条, 格式: {app_code} {tenant_id} {logo_filename}",
        )

    def handle(self, input_file, logo_dir, mapping_file, *args, **options):
        app_entries: list[tuple[str, str]] = self._parse_input_file(input_file)
        if not app_entries:
            self.stdout.write(self.style.WARNING("未读取到有效的应用条目, 退出"))
            return

        output_path = Path(logo_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        mapping_entries: list[tuple[str, str, str]] = []
        success_count, skip_count, fail_count = 0, 0, 0
        for app_code, tenant_id in app_entries:
            result = self._download_logo(app_code, tenant_id, output_path)
            if result is None:
                skip_count += 1
                continue
            if result:
                success_count += 1
                mapping_entries.append((app_code, tenant_id, result))
            else:
                fail_count += 1

        self._write_mapping_file(mapping_entries, mapping_file)
        self.stdout.write(
            self.style.SUCCESS(f"下载完成, 成功 {success_count} 条, 跳过 {skip_count} 条, 失败 {fail_count} 条")
        )

    def _parse_input_file(self, input_file: str) -> list[tuple[str, str]]:
        """解析输入文件, 获取应用列表"""
        entries: list[tuple[str, str]] = []
        input_path = Path(input_file)

        if not input_path.exists():
            self.stderr.write(self.style.ERROR(f"输入文件 {input_file} 不存在"))
            return entries

        try:
            with input_path.open("r", encoding="utf-8") as f:
                for line_num, row_line in enumerate(f, start=1):
                    line = row_line.strip()
                    if not line or line.startswith("#"):
                        continue

                    part = line.split()
                    if len(part) != 2:
                        self.stdout.write(self.style.WARNING(f"第 {line_num} 行格式错误, 已忽略"))
                        continue
                    entries.append((part[0], part[1]))
        except OSError as e:
            self.stderr.write(self.style.ERROR(f"解析输入文件 {input_file} 失败: {e}"))
            return entries

        self.stdout.write(self.style.SUCCESS(f"从输入文件中读取到 {len(entries)} 条有效数据"))
        return entries

    def _download_logo(self, app_code: str, tenant_id: str, output_dir: Path) -> str | None:
        """下载应用 Logo, 保存到输出目录

        :return: 成功时返回下载的 logo 文件名, 失败返回空字符串, 跳过返回 None
        """
        try:
            app = Application.objects.get(code=app_code, tenant_id=tenant_id)
        except Application.DoesNotExist:
            self.stdout.write(self.style.WARNING(f"应用 {app_code}({tenant_id}) 不存在, 已忽略"))
            return None

        if not app.has_customized_logo():
            self.stdout.write(self.style.WARNING(f"应用 {app_code}({tenant_id}) 没有自定义 Logo, 已忽略"))
            return None

        local_file_name = Path(app.logo.name).name
        local_file_path = output_dir / local_file_name

        try:
            # 通过 Django FileField 的 storage 后端读取远程文件
            with app.logo.storage.open(app.logo.name, "rb") as remote_file:
                content = remote_file.read()
            local_file_path.write_bytes(content)

            self.stdout.write(
                self.style.SUCCESS(f"应用 {app_code}({tenant_id}) Logo 下载成功, 保存到 {local_file_path}")
            )
        except (OSError, RequestError) as e:
            self.stderr.write(self.style.ERROR(f"应用 {app_code}({tenant_id}) Logo 下载失败: {e}"))
            return ""
        else:
            return local_file_name

    def _write_mapping_file(self, entries, mapping_file):
        """生成映射文件"""
        mapping_path = Path(mapping_file)
        mapping_path.parent.mkdir(parents=True, exist_ok=True)

        with mapping_path.open("w", encoding="utf-8") as f:
            for app_code, tenant_id, logo_name in entries:
                f.write(f"{app_code} {tenant_id} {logo_name}\n")
        self.stdout.write(self.style.SUCCESS(f"映射文件已生成, 保存到 {mapping_file}"))
