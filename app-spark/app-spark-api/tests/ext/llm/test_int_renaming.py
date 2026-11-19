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

"""Naming a project after the first thing its user said."""

from __future__ import annotations

import json
import logging

import pytest
from pydantic import ValidationError

from app_spark_api.core.projects.constants import PROJECT_NAME_MAX_LENGTH
from app_spark_api.ext.llm.int_renaming import (
    GENERATED_PROJECT_NAME_MIN_LENGTH,
    NAMING_PROMPT_MAX_LENGTH,
    PROJECT_NAMING_INSTRUCTIONS,
    GeneratedProjectName,
    generate_project_name,
)
from app_spark_api.infras.llm import DirectLLMConfig, FakeLLMConfig, LLMCallError, LLMClient
from tests.infras.llm.support import answer_with_outputs

logger = logging.getLogger(__name__)


def direct_client(transport) -> LLMClient:
    return LLMClient(DirectLLMConfig(model="deepseek:deepseek-v4-flash", api_key="sk-test"), transport=transport)


class TestGeneratedProjectName:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("番茄专注钟", "番茄专注钟"),
            ("  「番茄专注钟」。\n", "番茄专注钟"),
            ("《团队周报助手》", "团队周报助手"),
            ("记账", "记账"),
            ("**旅行清单**", "旅行清单"),
        ],
    )
    def test_strips_decoration(self, name, expected):
        assert GeneratedProjectName(name=name).name == expected

    @pytest.mark.parametrize("name", [None, "", "   \n  ", "「」。", "留空", "「无」", "null", "None"])
    def test_nothing_usable_is_no_name(self, name):
        assert GeneratedProjectName(name=name).name is None

    def test_name_may_be_left_out(self):
        assert GeneratedProjectName().name is None

    @pytest.mark.parametrize("name", ["钟", "一" * (PROJECT_NAME_MAX_LENGTH + 1), "番茄\n专注钟"])
    def test_rejects_names_that_do_not_fit(self, name):
        with pytest.raises(ValidationError):
            GeneratedProjectName(name=name)


class TestGenerateProjectName:
    async def test_returns_the_cleaned_name(self):
        llm = LLMClient(FakeLLMConfig(output={"name": "「番茄专注钟」"}))

        assert await generate_project_name("做一个番茄钟", llm=llm) == "番茄专注钟"

    @pytest.mark.parametrize("output", [{}, {"name": None}, {"name": ""}, {"name": "。"}])
    async def test_no_name_is_a_valid_answer(self, output):
        llm = LLMClient(FakeLLMConfig(output=output))

        assert await generate_project_name("你好", llm=llm) is None

    async def test_sends_the_prompt_with_naming_instructions(self):
        transport = answer_with_outputs({"name": "记账本"})

        await generate_project_name("  帮我做一个家庭记账本  ", llm=direct_client(transport))

        messages = transport.last_body["messages"]
        assert {"role": "system", "content": PROJECT_NAMING_INSTRUCTIONS} in messages
        assert messages[-1] == {"role": "user", "content": "帮我做一个家庭记账本"}

    @pytest.mark.parametrize(
        ("model", "expected"),
        [("deepseek:deepseek-v4-flash", "none"), ("deepseek:deepseek-reasoner", "medium")],
    )
    async def test_thinks_off_or_at_medium_effort(self, model, expected):
        transport = answer_with_outputs({"name": "番茄钟"})
        llm = LLMClient(DirectLLMConfig(model=model, api_key="sk-test"), transport=transport)

        await generate_project_name("做一个番茄钟", llm=llm)

        assert transport.last_body["reasoning_effort"] == expected

    async def test_long_prompt_is_cut_before_sending(self):
        transport = answer_with_outputs({"name": "长文"})

        await generate_project_name("长" * 5000, llm=direct_client(transport))

        sent = transport.last_body["messages"][-1]["content"]
        assert len(sent) == NAMING_PROMPT_MAX_LENGTH

    async def test_name_that_does_not_fit_is_answered_again(self):
        transport = answer_with_outputs({"name": "钟"}, {"name": "番茄钟"})

        assert await generate_project_name("做一个番茄钟", llm=direct_client(transport)) == "番茄钟"
        assert len(transport.requests) == 2

    async def test_name_that_never_fits_is_a_call_error(self):
        transport = answer_with_outputs(*[{"name": "钟"}] * 5)

        with pytest.raises(LLMCallError):
            await generate_project_name("做一个番茄钟", llm=direct_client(transport))


@pytest.mark.live_llm
class TestLiveGenerateProjectName:
    @pytest.mark.parametrize(
        "prompt",
        [
            pytest.param("做一个番茄钟，能统计我每天专注了多久", id="pomodoro"),
            pytest.param("帮团队做一个收集周报的小工具，每周五提醒大家填写，然后汇总给组长", id="weekly-report"),
            pytest.param("I want a page to track the books I've read this year", id="books-en"),
        ],
    )
    async def test_names_a_real_prompt(self, live_llm, prompt):
        name = await generate_project_name(prompt, llm=live_llm)

        logger.info("%s -> %s", prompt, name)
        assert name is not None
        assert GENERATED_PROJECT_NAME_MIN_LENGTH <= len(name) <= PROJECT_NAME_MAX_LENGTH

    @pytest.mark.parametrize("prompt", [pytest.param("你好", id="hello"), pytest.param("在吗？", id="ping")])
    async def test_leaves_a_vague_prompt_unnamed(self, live_llm, prompt):
        name = await generate_project_name(prompt, llm=live_llm)

        logger.info("%s -> %s", prompt, json.dumps(name, ensure_ascii=False))
        assert name is None
