# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from collections import defaultdict
from typing import List

from .models import DocumentaryLink
from .tags import Tag


class DocumentaryLinkAdvisor:
    """The documentary link advisor"""

    def search_by_tags(self, tags: List[Tag], limit: int = 5) -> List[DocumentaryLink]:
        """A simple algorithm which finds the most related links items by our typed tags

        - loop over all tag types of our subject
        - if the link object has any affinity tags with this tag type
            - True: check if any of them has the same tag value
                - True: score += 10 * MATCHED_TAGS
                - False: score -= 100
            - False: which means this link object was supposed to match "{tag_type}:*"
                - score += 1 * NUM_OF_SUBJECT_TAGS_IN_THIS_TYPE
        - multiply the score by link object's ({priority} + 1)

        :param tags: list of Tag objects
        :returns: list of DocumentaryLink objects
        """
        if not tags:
            return []

        subject_tags_by_type = defaultdict(set)
        for tag in tags:
            subject_tags_by_type[tag.tag_type].add(tag)

        results = []
        for link in DocumentaryLink.objects.all().order_by('pk'):
            score = 0
            for tag_type in subject_tags_by_type:
                link_tags = link.get_affinity_tags_by_type(tag_type)
                if not link_tags:
                    score += len(link_tags)
                    continue

                common_tags = set(link_tags) & subject_tags_by_type[tag_type]
                if common_tags:
                    score += 10 * len(common_tags)
                else:
                    score -= 100
            if score > 0:
                results.append({"score": score * link.priority, "link": link})
        results.sort(key=lambda item: item["score"], reverse=True)
        return [item["link"] for item in results[:limit]]
