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
from builtins import object
from typing import List, Type

from django.utils.encoding import force_text


class Tag(object):
    """Tag for recommendation

    :param str tag_type: tag type string
    :param str tag_value: tag value string, if should be lower formed string
    """

    def __init__(self, tag_type, tag_value):
        self.tag_type = force_text(tag_type)
        self.tag_value = force_text(tag_value)

    def __str__(self):
        return u"{}:{}".format(self.tag_type, self.tag_value)

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        if isinstance(other, Tag):
            return self.__hash__() == other.__hash__()
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)


class BaseFixedTypeTag(Tag):
    tag_type: str = ''

    def __init__(self, tag_value):
        super(BaseFixedTypeTag, self).__init__(self.tag_type, tag_value)


PlatPanelTag = type("PlatPanelTag", (BaseFixedTypeTag,), {"tag_type": "plat-panel"})
AppPLTag = type("AppPLTag", (BaseFixedTypeTag,), {"tag_type": "app-pl"})
AppSDKTag = type("AppSDKTag", (BaseFixedTypeTag,), {"tag_type": "app-sdk"})
AppFeatureTag = type("AppFeatureTag", (BaseFixedTypeTag,), {"tag_type": "app-feature"})
DeploymentFailureTag = type("DeploymentFailureTag", (BaseFixedTypeTag,), {"tag_type": "deploy-failure"})
DeployPhaseTag = type("DeployPhaseTag", (BaseFixedTypeTag,), {"tag_type": "deploy_phase"})


TAG_TYPES: List[Type[BaseFixedTypeTag]] = [
    PlatPanelTag,
    AppPLTag,
    AppSDKTag,
    AppFeatureTag,
    DeploymentFailureTag,
    DeployPhaseTag,
]
TAG_TYPES_MAP = {t.tag_type: t for t in TAG_TYPES}


class TagSet(object):
    """All tags set"""

    def __init__(self):
        self.tags = {}

    def get(self, tag_str):
        """Get a tag object by tag string"""
        tag = self.tags.get(tag_str)
        if not tag:
            raise ValueError("tag {} does not exists".format(tag_str))
        return tag

    def get_tags(self, tag_str_list):
        """Get a tag object by a list of tag string"""
        return [self.get(tag_str) for tag_str in tag_str_list]

    def add(self, tag):
        """Add a tag object to this set"""
        assert isinstance(tag, Tag), "must be Tag type"
        self.tags[str(tag)] = tag

    def add_tags(self, tags):
        """Add multiple tags at once"""
        [self.add(tag) for tag in tags]

    def validate_tags(self, tags):
        """Validates if given tag objects is valid

        :param tags: list of Tag objects
        """
        for tag in tags:
            if str(tag) not in self.tags:
                raise ValueError("tag {} is not a valid tag".format(tag))


# Default built-in tags
_default_tag_set = TagSet()
_default_tag_set.add_tags(
    [
        AppPLTag("python"),
        AppSDKTag("django"),
        AppSDKTag("blueapps"),
        AppSDKTag("celery"),
        AppSDKTag("gunicorn"),
        AppPLTag("go"),
        AppSDKTag("beego"),
        AppPLTag("nodejs"),
        AppSDKTag("vuejs"),
        AppPLTag("php"),
        AppSDKTag("laravel"),
        AppFeatureTag("has_single_processes"),
        AppFeatureTag("has_many_processes"),
        AppFeatureTag("has_multiple_modules"),
        AppFeatureTag("web-console"),
        PlatPanelTag("app_created"),
        PlatPanelTag("app_deployment"),
        PlatPanelTag("app_processes"),
    ]
)


# A shortcut for retrieve pre-defined tags
force_tag = _default_tag_set.get


def get_default_tagset():
    return _default_tag_set


def get_dynamic_tag(tag_str: str) -> Tag:
    """Get dynamic tag object by given tag string

    :param tag_str: string format tag, eg: "app-pl:python"
    :raises: ValueError when given string is not a valid tag string
    """
    try:
        tag_type, tag_value = tag_str.split(':')
        tag_cls = TAG_TYPES_MAP[tag_type]
    except (ValueError, KeyError):
        raise ValueError(f'"{tag_str}" is not a valid tag string')
    return tag_cls(tag_value)
