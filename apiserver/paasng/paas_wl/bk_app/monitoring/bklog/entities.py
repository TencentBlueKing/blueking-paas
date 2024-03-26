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
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional


@dataclass
class MatchExpression:
    key: str
    operator: Literal["IN", "NotIN", "Exists", "DoesNotExist"]
    values: Optional[List[str]] = None


@dataclass
class LabelSelector:
    """K8S LabelSelector is a label query over a set of resources.
    The result of matchLabels and matchExpressions are ANDed. An empty
    label selector matches all objects. A null label selector matches
    no objects.

    :param matchExpressions: matchExpressions is a list of label selector requirements. The requirements are ANDed.
    :param matchLabels: matchLabels is a map of {key,value} pairs.
            A single {key,value} in the matchLabels map is equivalent to an element of matchExpressions,
            whose key field is "key", the operator is "In", and the values array contains only "value".
            The requirements are ANDed.
    """

    matchExpressions: List[MatchExpression] = field(default_factory=list)
    matchLabels: Dict[str, str] = field(default_factory=dict)


@dataclass
class LogFilterCondition:
    """Condition is bkunifylogbeat filter rule"""

    index: int
    key: str
    op: str
