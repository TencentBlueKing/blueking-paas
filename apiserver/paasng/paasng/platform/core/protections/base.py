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
"""Preconditions for doing something"""
import logging
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import List

from paasng.platform.core.protections.exceptions import ConditionNotMatched

logger = logging.getLogger(__name__)


class BaseCondition(metaclass=ABCMeta):
    @abstractmethod
    def validate(self):
        """Raise ConditionNotMatched exception if validate failed"""


@dataclass
class FailedCondition:
    message: str
    action_name: str


class ProtectionStatus:
    def __init__(self, failed_conditions: List[ConditionNotMatched]):
        self.failed_conditions = [FailedCondition(**item.as_dict()) for item in failed_conditions]

    @property
    def activated(self) -> bool:
        """protection is activated or not, default to False"""
        return len(self.failed_conditions) > 0

    @property
    def reason(self) -> str:
        """the detailed reason of why resource is protected,
        if there are multiple reasons, only return the first one."""
        return str(self.failed_conditions[0].message) if self.activated else ''

    def __eq__(self, other) -> bool:
        if not isinstance(other, ProtectionStatus):
            return False
        return self.failed_conditions == other.failed_conditions


class BaseConditionChecker:
    conditions: List[BaseCondition]

    def perform(self) -> ProtectionStatus:
        """perform condition check

        :returns: if any conditions not matched, return the list of detailed exceptions
        """
        failed_conditions = []
        for condition in self.conditions:
            try:
                condition.validate()
            except ConditionNotMatched as e:
                failed_conditions.append(e)

        if failed_conditions:
            logger.info("%s is not prepare for %s", self, "\n".join([str(x.message) for x in failed_conditions]))
        return ProtectionStatus(failed_conditions)

    @property
    def all_matched(self) -> bool:
        """Check if application can publish to market"""
        return not self.perform().activated
