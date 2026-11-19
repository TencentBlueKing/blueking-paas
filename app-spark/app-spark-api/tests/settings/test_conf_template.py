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

"""conf.yaml.tpl is the reference for every setting, so it must list exactly what the code reads."""

import re
from pathlib import Path

SETTINGS_DIR = Path(__file__).resolve().parents[2] / "app_spark_api" / "settings"
TEMPLATE = Path(__file__).resolve().parents[2] / "conf.yaml.tpl"


def test_template_lists_exactly_the_settings_the_code_reads():
    code = "".join(path.read_text(encoding="utf-8") for path in SETTINGS_DIR.glob("*.py"))
    read_by_code = set(re.findall(r'settings\.get\(\s*"([A-Z][A-Z0-9_]*)"', code))
    # Top-level keys only: nested fields are indented under their parent.
    in_template = set(re.findall(r"^# ([A-Z][A-Z0-9_]*):", TEMPLATE.read_text(encoding="utf-8"), re.MULTILINE))

    assert read_by_code - in_template == set(), "settings missing from conf.yaml.tpl"
    assert in_template - read_by_code == set(), "conf.yaml.tpl lists settings the code no longer reads"
