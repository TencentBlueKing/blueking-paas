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
from blue_krill import termcolors
from django.conf import settings


def make_style(*args, **kwargs):
    colorful = termcolors.make_style(*args, **kwargs)

    def dynamic_style(text):
        if settings.COLORFUL_TERMINAL_OUTPUT:
            return colorful(text)
        return termcolors.no_color(text)

    return dynamic_style


class Style:
    """
    Valid colors:
        ANSI Color: 'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'
        XTerm Color: [0-256]
        Hex Color: #000000 ~ #FFFFFF

    see also: https://en.wikipedia.org/wiki/X11_color_names#Clashes_between_web_and_X11_colors_in_the_CSS_color_scheme

    Valid options:
        'bold', 'underscore', 'blink', 'reverse', 'conceal', 'noreset'
    """

    Title = make_style(fg='#c4c6cc', opts=('bold',))
    Error = make_style(fg='#e82f2f', opts=('bold',))
    Warning = make_style(fg='#ff9c01', opts=('bold',))
    Comment = make_style(fg='#3a84ff', opts=('bold',))
    NoColor = termcolors.no_color

    Black = make_style(fg='black', opts=('bold',))
    Red = make_style(fg='red', opts=('bold',))
    Green = make_style(fg='green', opts=('bold',))
    Yellow = make_style(fg='yellow', opts=('bold',))
    Blue = make_style(fg='blue', opts=('bold',))
    Magenta = make_style(fg='magenta', opts=('bold',))
    Cyan = make_style(fg='cyan', opts=('bold',))
    White = make_style(fg='white', opts=('bold',))
