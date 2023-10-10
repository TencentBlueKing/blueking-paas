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
import base64
import re
from typing import Dict

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.deconstruct import deconstructible
from django.utils.encoding import force_text
from past.builtins import basestring

from paasng.core.region.models import Region, RegionList, filter_region_by_name

RE_APP_CODE = re.compile(r'^[a-z0-9-]{1,16}$')
RE_APP_SEARCH = re.compile(u'[\u4300-\u9fa5\\w_\\-\\d]{1,20}')

RE_CONFIG_VAR_KEY = re.compile(r'^[A-Z][A-Z0-9_]*$')


@deconstructible
class DnsSafeNameValidator:
    """DNS name safe validator"""

    def __init__(self, resource_type: str):
        self.resource_type = resource_type
        self.message = f"{self.resource_type} 不能以 - 或数字开头或结尾, 且不能为纯数字"
        self.validator = RegexValidator('^(?![0-9]+.*$)(?!-)[a-zA-Z0-9-]{,63}(?<!-)$', message=self.message)

    def __call__(self, value):
        value = force_text(value)
        self.validator(value)


@deconstructible
class ReservedWordValidator:
    """Reserved word validator"""

    def __init__(self, resource_type: str):
        self.resource_type = resource_type
        self.reserved_word = ['-dot-', '0us0', '--', '-m-']
        self.message = f"{self.resource_type} 不能包含保留字 {self.reserved_word}"
        self.validator = RegexValidator("|".join(self.reserved_word), message=self.message, inverse_match=True)

    def __call__(self, value):
        value = force_text(value)
        self.validator(value)


@deconstructible
class RegionListValidator:
    def __call__(self, value):
        if isinstance(value, basestring):
            if not self.is_formatted_string(value):
                raise ValidationError("please supply valid string as 'ieod;tencent;clouds'")
            return value

        if isinstance(value, RegionList) and all(isinstance(x, Region) for x in value):
            region_names = ';'.join([x.name for x in value])
            return region_names
        raise ValidationError("please supply valid RegionList")

    @staticmethod
    def is_formatted_string(value):
        try:
            region_list = filter_region_by_name(value.split(';'))
        except Exception:
            return False
        else:
            # make sure region not repeat
            if len(region_list) == len(set(region_list)) == len(value.split(';')):
                return True
            return False


@deconstructible
class Base64Validator:
    def __call__(self, value):
        try:
            base64.b64decode(value)
        except Exception:
            raise ValidationError("content is not a base64 encoded obj.")


def str2bool(value):
    TRUE_VALUES = {
        't',
        'T',
        'y',
        'Y',
        'yes',
        'YES',
        'true',
        'True',
        'TRUE',
        'on',
        'On',
        'ON',
        '1',
    }
    FALSE_VALUES = {
        'f',
        'F',
        'n',
        'N',
        'no',
        'NO',
        'false',
        'False',
        'FALSE',
        'off',
        'Off',
        'OFF',
        '0',
    }
    if value in TRUE_VALUES:
        return True
    elif value in FALSE_VALUES:
        return False
    else:
        raise ValueError(f"Given value({value}) not valid!")


PROC_TYPE_PATTERN = re.compile(r'^[a-zA-Z0-9]([-a-zA-Z0-9])*$')
PROC_TYPE_MAX_LENGTH = 12


def validate_procfile(procfile: Dict[str, str]) -> Dict[str, str]:
    """Validate proc type format
    :param procfile:
    :return: validated procfile, which all key is lower case.
    :raise: django.core.exceptions.ValidationError
    """
    for proc_type in procfile.keys():
        if not PROC_TYPE_PATTERN.match(proc_type):
            raise ValidationError(
                f'Invalid proc type: {proc_type}, must match ' f'pattern {PROC_TYPE_PATTERN.pattern}'
            )
        if len(proc_type) > PROC_TYPE_MAX_LENGTH:
            raise ValidationError(
                f'Invalid proc type: {proc_type}, must not ' f'longer than {PROC_TYPE_MAX_LENGTH} characters'
            )

    # Formalize procfile data and return
    return {k.lower(): v for k, v in procfile.items()}
