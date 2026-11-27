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

"""Fast schema validation and Runtime conversion tests for conversation API entities."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app_spark_api.agent.conversations.entities import (
    AskUserAnswerSchema,
    AskUserOptionSchema,
    AskUserQuestionSchema,
    AskUserResponseSchema,
    PendingQuestionSchema,
    StartRunRequest,
)
from app_spark_api.agent.runtime.entities import (
    AskUserAnswerInput,
    AskUserOption,
    AskUserQuestion,
    AskUserResponseInput,
    PendingQuestion,
)


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"content": "hello"}, id="text-only"),
        pytest.param({"attachment_ids": [str(uuid4())]}, id="attachment-only"),
        pytest.param(
            {"ask_user_responses": [{"tool_call_id": "tc-1", "cancelled": True}]},
            id="ask-user-only",
        ),
    ],
)
def test_start_run_request_accepts_each_valid_input_mode(payload):
    req = StartRunRequest.model_validate(payload)
    assert req is not None


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="all-empty"),
        pytest.param({"content": "   "}, id="whitespace-only"),
        pytest.param(
            {
                "content": "also hi",
                "ask_user_responses": [{"tool_call_id": "tc-1", "cancelled": True}],
            },
            id="content-and-ask-user",
        ),
        pytest.param(
            {
                "attachment_ids": [str(uuid4())],
                "ask_user_responses": [{"tool_call_id": "tc-1", "cancelled": True}],
            },
            id="attachments-and-ask-user",
        ),
        pytest.param(
            {"attachment_ids": ["00000000-0000-0000-0000-000000000001"] * 2},
            id="duplicate-attachments",
        ),
        pytest.param(
            {"ask_user_responses": [{"tool_call_id": "   ", "cancelled": True}]},
            id="blank-tool-call-id",
        ),
        pytest.param(
            {"ask_user_responses": [{"tool_call_id": "tc-1", "answers": [{"header": "   ", "selected": ["A"]}]}]},
            id="blank-answer-header",
        ),
    ],
)
def test_start_run_request_rejects_invalid_combinations_and_blank_identifiers(payload):
    with pytest.raises(ValidationError):
        StartRunRequest.model_validate(payload)


def test_ask_user_response_schema_converts_to_runtime_input():
    schema = AskUserResponseSchema(
        tool_call_id=" tc-1 ",
        answers=[
            AskUserAnswerSchema(header=" Style ", selected=["Clean"]),
            AskUserAnswerSchema(header="Notes", custom_answer="Keep it minimal"),
        ],
    )

    assert schema.to_runtime_input() == AskUserResponseInput(
        tool_call_id="tc-1",
        answers=(
            AskUserAnswerInput(header="Style", selected=("Clean",)),
            AskUserAnswerInput(header="Notes", custom_answer="Keep it minimal"),
        ),
        cancelled=False,
    )


def test_pending_question_schema_converts_from_runtime():
    runtime_item = PendingQuestion(
        tool_call_id="tc-1",
        questions=(
            AskUserQuestion(
                header="Theme",
                question="Pick a theme",
                options=(AskUserOption(label="Dark", description="Low glare"),),
                multi_select=True,
            ),
        ),
    )

    assert PendingQuestionSchema.from_runtime(runtime_item) == PendingQuestionSchema(
        tool_call_id="tc-1",
        questions=[
            AskUserQuestionSchema(
                header="Theme",
                question="Pick a theme",
                options=[AskUserOptionSchema(label="Dark", description="Low glare")],
                multi_select=True,
            )
        ],
    )
