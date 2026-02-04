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

import textwrap

from django.core.management.base import BaseCommand, CommandError

from paasng.platform.agent_sandbox.sandbox import AgentSandboxFactory
from paasng.platform.applications.models import Application


class Command(BaseCommand):
    help = "demo for agent sandbox pod lifecycle"

    def add_arguments(self, parser):
        parser.add_argument("--app-code", required=True, help="application code")

    def handle(self, *args, **options):
        app_code = options["app_code"]
        try:
            app = Application.objects.get(code=app_code)
        except Application.DoesNotExist as exc:
            raise CommandError(f"Application {app_code} not found") from exc

        self.stdout.write(self.style.WARNING("Creating sandbox..."))
        factory = AgentSandboxFactory(app)
        sandbox = factory.create()
        self.stdout.write(self.style.SUCCESS(f"Sandbox created: {sandbox.entity.name}"))

        try:
            result = sandbox.exec("python -V")
            self.stdout.write(self.style.SUCCESS(f"exec stdout: {result.stdout.strip()}"))

            # Upload and download a file
            content = textwrap.dedent(
                """
                print("hello from agent sandbox")
                """
            ).lstrip()
            remote_path = f"{sandbox.entity.workdir}/hello.py"
            sandbox.upload_file(content.encode(), remote_path)
            downloaded = sandbox.download_file(remote_path).decode("utf-8", errors="replace")
            self.stdout.write(self.style.SUCCESS(f"downloaded content: {downloaded.strip()}"))

            # Run Python code
            ret = sandbox.code_run("for i in range(10): print(i)")
            self.stdout.write(self.style.SUCCESS(f"code_run stdout:\n{ret.stdout}"))

            logs = sandbox.get_logs(tail_lines=50)
            self.stdout.write(self.style.SUCCESS(f"logs (tail):\n{logs}"))
        finally:
            self.stdout.write(self.style.WARNING("Destroying sandbox..."))
            factory.destroy(sandbox)
            self.stdout.write(self.style.SUCCESS("Sandbox destroyed"))
