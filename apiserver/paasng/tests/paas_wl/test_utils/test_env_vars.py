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
from paas_wl.utils.env_vars import VarsRenderContext, render_vars_dict


def test_render_vars_dict():
    d = {
        "BKPAAS_PROCESS_TYPE": "{{bk_var_process_type}}",
        "OTHER_PRE_LOG_NAME_PREFIX": "foo-{{bk_var_process_type}}",
        # with valid name but variable does not match
        "OTHER_PRE_PROCESS_TYPE": "{{another_var}}",
        "FOO": "some random value",
        # the variable matches but the name is not in whitelist
        "BAR": "{{bk_var_process_type}}",
        "FOO_BAR": "{{some_var}}",
    }
    assert render_vars_dict(d, VarsRenderContext(process_type="web")) == {
        "BKPAAS_PROCESS_TYPE": "web",
        "OTHER_PRE_LOG_NAME_PREFIX": "foo-web",
        "OTHER_PRE_PROCESS_TYPE": "{{another_var}}",
        "FOO": "some random value",
        "BAR": "{{bk_var_process_type}}",
        "FOO_BAR": "{{some_var}}",
    }
