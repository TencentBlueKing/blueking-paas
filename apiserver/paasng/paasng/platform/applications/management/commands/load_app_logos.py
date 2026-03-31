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

"""批量导入应用图标

Usage:
    python manage.py load_app_logos \
      --mapping-file /path/to/mapping.txt \
      --logo-dir /path/to/logos

输入映射文件格式(每行一条):
    {app_code} {tenant_id} {logo_filename}
"""

from pathlib import Path

from bkstorages.backends.bkrepo import RequestError
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from paasng.platform.applications.models import Application
from paasng.platform.applications.signals import application_logo_updated


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--mapping-file",
            dest="mapping_file",
            required=True,
            type=str,
            help="映射文件路径, 每行一条, 格式: {app_code} {tenant_id} {logo_filename}",
        )
        parser.add_argument("--logo-dir", dest="logo_dir", required=True, type=str, help="logo 文件所在目录路径")

    def handle(self, mapping_file, logo_dir, *args, **options):
        app_entries: list[tuple[str, str, str]] = self._parse_mapping_file(mapping_file)
        if not app_entries:
            self.stderr.write(self.style.ERROR("未读取到有效的映射文件条目, 退出"))
            return

        logo_dir_path = Path(logo_dir)
        if not logo_dir_path.exists():
            self.stderr.write(self.style.ERROR(f"logo 文件目录不存在: {logo_dir}"))
            return

        success_count, skip_count, fail_count = 0, 0, 0
        for app_code, tenant_id, logo_filename in app_entries:
            result = self._upload_logo(app_code, tenant_id, logo_dir_path, logo_filename)
            if result is None:
                skip_count += 1
            elif result:
                success_count += 1
            else:
                fail_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"成功上传 {success_count} 个图标, 跳过 {skip_count} 个, 失败 {fail_count} 个")
        )

    def _parse_mapping_file(self, mapping_file: str) -> list[tuple[str, str, str]]:
        """解析映射文件, 获取应用与 logo 文件的对应关系

        文件格式(每行一条):
            {app_code} {tenant_id} {logo_filename}
        """

        entries: list[tuple[str, str, str]] = []
        mapping_file_path = Path(mapping_file)

        if not mapping_file_path.exists():
            self.stderr.write(self.style.ERROR(f"映射文件不存在: {mapping_file}"))
            return entries

        try:
            with mapping_file_path.open("r", encoding="utf-8") as f:
                for line_num, row_line in enumerate(f, start=1):
                    line = row_line.strip()
                    if not line or line.startswith("#"):
                        continue

                    parts = line.split()
                    if len(parts) != 3:
                        self.stderr.write(self.style.ERROR(f"第 {line_num} 行格式错误: {line}"))
                        continue

                    entries.append((parts[0], parts[1], parts[2]))
        except OSError as e:
            self.stderr.write(self.style.ERROR(f"解析映射文件失败: {e}"))
            return entries

        self.stdout.write(self.style.SUCCESS(f"从映射文件中读取到 {len(entries)} 条有效数据"))
        return entries

    def _upload_logo(self, app_code: str, tenant_id: str, logo_dir_path: Path, logo_filename: str) -> bool | None:
        """上传单个应用的 logo

        :return: True 上传成功, False 上传失败, None 跳过
        """
        logo_path = logo_dir_path / logo_filename
        if not logo_path.exists():
            self.stderr.write(self.style.ERROR(f"应用 {app_code}({tenant_id}) logo 文件不存在: {logo_path}"))
            return None

        try:
            app = Application.objects.get(code=app_code, tenant_id=tenant_id)
        except Application.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"应用 {app_code}({tenant_id}) 不存在"))
            return None

        try:
            content = logo_path.read_bytes()
            # 使用 Django FileField 的 save 方法上传文件
            app.logo.save(logo_filename, ContentFile(content), save=False)
            app.save(update_fields=["logo"])

            # 发送信号触发额外处理
            application_logo_updated.send(sender=Application, application=app)

            self.stdout.write(self.style.SUCCESS(f"应用 {app_code}({tenant_id}) logo 上传成功"))
        except (OSError, RequestError) as e:
            self.stderr.write(self.style.ERROR(f"应用 {app_code}({tenant_id}) logo 上传失败: {e}"))
            return False
        else:
            return True
