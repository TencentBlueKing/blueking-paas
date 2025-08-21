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

import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """Token Response
    spec: https://github.com/distribution/distribution/blob/main/docs/spec/auth/token.md#token-response-fields

    """

    token: str = Field(
        ...,
        description="An opaque Bearer token that clients should "
        "supply to subsequent requests in the Authorization header.",
    )
    access_token: Optional[str] = Field(
        None,
        description="For compatibility with OAuth 2.0, we will also accept token under the name access_token",
    )
    issued_at: Optional[datetime.datetime] = Field(
        None,
        description="The RFC3339-serialized UTC standard time at which a given token was issued.",
    )
    expires_in: Optional[int] = Field(
        None,
        description="The duration in seconds since the token was issued that it will remain valid. ",
    )
    refresh_token: Optional[str] = Field(
        None,
        description="Token which can be used to get additional access tokens "
        "for the same subject with different scopes. ",
    )
