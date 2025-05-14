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

import logging
from typing import Optional

logger = logging.getLogger(__name__)

RESET = "\x1b[0m"
OPT_MAPS = {"bold": "\x1b[1m", "underscore": "\x1b[4m", "blink": "\x1b[5m", "reverse": "\x1b[7m", "conceal": "\x1b[8m"}
ANSI_MAPS = {
    color: str(idx)
    for idx, color in enumerate(["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"])
}


def colorize(text: str = "", fg: Optional[str] = None, bg: Optional[str] = None, opts: tuple = ()):
    """
    Return your text, enclosed in ANSI graphics codes.

    Depends on the keyword arguments 'fg' and 'bg', and the contents of
    the opts tuple/list.

    Return the RESET code if no parameters are given.

    Valid colors:
        ANSI Color: 'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'
        XTerm Color: [0-256]
        Hex Color: #000000 ~ #FFFFFF
    see also: https://en.wikipedia.org/wiki/X11_color_names#Clashes_between_web_and_X11_colors_in_the_CSS_color_scheme

    Valid options:
        'bold'
        'underscore'
        'blink'
        'reverse'
        'conceal'
        'noreset' - string will not be auto-terminated with the RESET code

    Examples:
        colorize('hello', fg='red', bg='blue', opts=('blink',))
        colorize()
        colorize('goodbye', opts=('underscore',))
        print(colorize('first line', fg='red', opts=('noreset',)))
        print('this should be red too')
        print(colorize('and so should this'))
        print('this should not be red')
    """
    code_list = []
    if text == "" and len(opts) == 1 and opts[0] == "reset":
        return RESET
    if fg is not None:
        code_list.append(pick_color(fg, position="fg"))
    if bg is not None:
        code_list.append(pick_color(bg, position="bg"))
    for o in opts:
        if o in OPT_MAPS:
            code_list.append(OPT_MAPS[o])
    if "noreset" not in opts:
        text = f"{text}{RESET}"

    code_list.append(text)
    return "".join(code_list)


def make_style(fg: Optional[str] = None, bg: Optional[str] = None, opts: tuple = ()):
    """
    Return a function with default parameters for colorize()

    Example:
        bold_red = make_style(opts=('bold',), fg='red')
        KEYWORD = make_style(fg='yellow')
        COMMENT = make_style(fg='blue', opts=('bold',))
    """
    return lambda text: colorize(text, fg, bg, opts)


def pick_color(color: str = "black", position: str = "fg"):
    position_code = "38" if position == "fg" else "48"
    if color.startswith("#"):
        return f"\x1b[{position_code};{_pick_color_by_rgb(color)}"
    return f"\x1b[{position_code};{_pick_color_by_code(color)}"


def no_color(text):
    return text


def _pick_color_by_code(color: str = "black"):
    code = str(color).lower()
    code = ANSI_MAPS.get(code, code)
    if code not in XTERM_PALETTE:
        logger.warning("输入不合法, 转换成黑色.")
        code = "0"
    return f"5;{code}m"


def _pick_color_by_rgb(color: str = "#000"):
    if color.startswith("#"):
        color = color.lstrip("#")
    if len(color) == 3:
        r = int(color[0], 16)
        g = int(color[1], 16)
        b = int(color[2], 16)
    elif len(color) == 6:
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
    else:
        logger.warning("输入不合法, 转换成黑色.")
        r = g = b = 0
    return f"2;{r};{g};{b}m"


# XTerm 调色板
# XTerm Color Code To RGB Color
XTERM_PALETTE = {
    "0": [0, 0, 0],
    "1": [187, 0, 0],
    "2": [0, 187, 0],
    "3": [187, 187, 0],
    "4": [0, 0, 187],
    "5": [187, 0, 187],
    "6": [0, 187, 187],
    "7": [255, 255, 255],
    "8": [85, 85, 85],
    "9": [255, 85, 85],
    "10": [0, 255, 0],
    "11": [255, 255, 85],
    "12": [85, 85, 255],
    "13": [255, 85, 255],
    "14": [85, 255, 255],
    "15": [255, 255, 255],
    "16": [0, 0, 0],
    "17": [0, 0, 95],
    "18": [0, 0, 135],
    "19": [0, 0, 175],
    "20": [0, 0, 215],
    "21": [0, 0, 255],
    "22": [0, 95, 0],
    "23": [0, 95, 95],
    "24": [0, 95, 135],
    "25": [0, 95, 175],
    "26": [0, 95, 215],
    "27": [0, 95, 255],
    "28": [0, 135, 0],
    "29": [0, 135, 95],
    "30": [0, 135, 135],
    "31": [0, 135, 175],
    "32": [0, 135, 215],
    "33": [0, 135, 255],
    "34": [0, 175, 0],
    "35": [0, 175, 95],
    "36": [0, 175, 135],
    "37": [0, 175, 175],
    "38": [0, 175, 215],
    "39": [0, 175, 255],
    "40": [0, 215, 0],
    "41": [0, 215, 95],
    "42": [0, 215, 135],
    "43": [0, 215, 175],
    "44": [0, 215, 215],
    "45": [0, 215, 255],
    "46": [0, 255, 0],
    "47": [0, 255, 95],
    "48": [0, 255, 135],
    "49": [0, 255, 175],
    "50": [0, 255, 215],
    "51": [0, 255, 255],
    "52": [95, 0, 0],
    "53": [95, 0, 95],
    "54": [95, 0, 135],
    "55": [95, 0, 175],
    "56": [95, 0, 215],
    "57": [95, 0, 255],
    "58": [95, 95, 0],
    "59": [95, 95, 95],
    "60": [95, 95, 135],
    "61": [95, 95, 175],
    "62": [95, 95, 215],
    "63": [95, 95, 255],
    "64": [95, 135, 0],
    "65": [95, 135, 95],
    "66": [95, 135, 135],
    "67": [95, 135, 175],
    "68": [95, 135, 215],
    "69": [95, 135, 255],
    "70": [95, 175, 0],
    "71": [95, 175, 95],
    "72": [95, 175, 135],
    "73": [95, 175, 175],
    "74": [95, 175, 215],
    "75": [95, 175, 255],
    "76": [95, 215, 0],
    "77": [95, 215, 95],
    "78": [95, 215, 135],
    "79": [95, 215, 175],
    "80": [95, 215, 215],
    "81": [95, 215, 255],
    "82": [95, 255, 0],
    "83": [95, 255, 95],
    "84": [95, 255, 135],
    "85": [95, 255, 175],
    "86": [95, 255, 215],
    "87": [95, 255, 255],
    "88": [135, 0, 0],
    "89": [135, 0, 95],
    "90": [135, 0, 135],
    "91": [135, 0, 175],
    "92": [135, 0, 215],
    "93": [135, 0, 255],
    "94": [135, 95, 0],
    "95": [135, 95, 95],
    "96": [135, 95, 135],
    "97": [135, 95, 175],
    "98": [135, 95, 215],
    "99": [135, 95, 255],
    "100": [135, 135, 0],
    "101": [135, 135, 95],
    "102": [135, 135, 135],
    "103": [135, 135, 175],
    "104": [135, 135, 215],
    "105": [135, 135, 255],
    "106": [135, 175, 0],
    "107": [135, 175, 95],
    "108": [135, 175, 135],
    "109": [135, 175, 175],
    "110": [135, 175, 215],
    "111": [135, 175, 255],
    "112": [135, 215, 0],
    "113": [135, 215, 95],
    "114": [135, 215, 135],
    "115": [135, 215, 175],
    "116": [135, 215, 215],
    "117": [135, 215, 255],
    "118": [135, 255, 0],
    "119": [135, 255, 95],
    "120": [135, 255, 135],
    "121": [135, 255, 175],
    "122": [135, 255, 215],
    "123": [135, 255, 255],
    "124": [175, 0, 0],
    "125": [175, 0, 95],
    "126": [175, 0, 135],
    "127": [175, 0, 175],
    "128": [175, 0, 215],
    "129": [175, 0, 255],
    "130": [175, 95, 0],
    "131": [175, 95, 95],
    "132": [175, 95, 135],
    "133": [175, 95, 175],
    "134": [175, 95, 215],
    "135": [175, 95, 255],
    "136": [175, 135, 0],
    "137": [175, 135, 95],
    "138": [175, 135, 135],
    "139": [175, 135, 175],
    "140": [175, 135, 215],
    "141": [175, 135, 255],
    "142": [175, 175, 0],
    "143": [175, 175, 95],
    "144": [175, 175, 135],
    "145": [175, 175, 175],
    "146": [175, 175, 215],
    "147": [175, 175, 255],
    "148": [175, 215, 0],
    "149": [175, 215, 95],
    "150": [175, 215, 135],
    "151": [175, 215, 175],
    "152": [175, 215, 215],
    "153": [175, 215, 255],
    "154": [175, 255, 0],
    "155": [175, 255, 95],
    "156": [175, 255, 135],
    "157": [175, 255, 175],
    "158": [175, 255, 215],
    "159": [175, 255, 255],
    "160": [215, 0, 0],
    "161": [215, 0, 95],
    "162": [215, 0, 135],
    "163": [215, 0, 175],
    "164": [215, 0, 215],
    "165": [215, 0, 255],
    "166": [215, 95, 0],
    "167": [215, 95, 95],
    "168": [215, 95, 135],
    "169": [215, 95, 175],
    "170": [215, 95, 215],
    "171": [215, 95, 255],
    "172": [215, 135, 0],
    "173": [215, 135, 95],
    "174": [215, 135, 135],
    "175": [215, 135, 175],
    "176": [215, 135, 215],
    "177": [215, 135, 255],
    "178": [215, 175, 0],
    "179": [215, 175, 95],
    "180": [215, 175, 135],
    "181": [215, 175, 175],
    "182": [215, 175, 215],
    "183": [215, 175, 255],
    "184": [215, 215, 0],
    "185": [215, 215, 95],
    "186": [215, 215, 135],
    "187": [215, 215, 175],
    "188": [215, 215, 215],
    "189": [215, 215, 255],
    "190": [215, 255, 0],
    "191": [215, 255, 95],
    "192": [215, 255, 135],
    "193": [215, 255, 175],
    "194": [215, 255, 215],
    "195": [215, 255, 255],
    "196": [255, 0, 0],
    "197": [255, 0, 95],
    "198": [255, 0, 135],
    "199": [255, 0, 175],
    "200": [255, 0, 215],
    "201": [255, 0, 255],
    "202": [255, 95, 0],
    "203": [255, 95, 95],
    "204": [255, 95, 135],
    "205": [255, 95, 175],
    "206": [255, 95, 215],
    "207": [255, 95, 255],
    "208": [255, 135, 0],
    "209": [255, 135, 95],
    "210": [255, 135, 135],
    "211": [255, 135, 175],
    "212": [255, 135, 215],
    "213": [255, 135, 255],
    "214": [255, 175, 0],
    "215": [255, 175, 95],
    "216": [255, 175, 135],
    "217": [255, 175, 175],
    "218": [255, 175, 215],
    "219": [255, 175, 255],
    "220": [255, 215, 0],
    "221": [255, 215, 95],
    "222": [255, 215, 135],
    "223": [255, 215, 175],
    "224": [255, 215, 215],
    "225": [255, 215, 255],
    "226": [255, 255, 0],
    "227": [255, 255, 95],
    "228": [255, 255, 135],
    "229": [255, 255, 175],
    "230": [255, 255, 215],
    "231": [255, 255, 255],
    "232": [8, 8, 8],
    "233": [18, 18, 18],
    "234": [28, 28, 28],
    "235": [38, 38, 38],
    "236": [48, 48, 48],
    "237": [58, 58, 58],
    "238": [68, 68, 68],
    "239": [78, 78, 78],
    "240": [88, 88, 88],
    "241": [98, 98, 98],
    "242": [108, 108, 108],
    "243": [118, 118, 118],
    "244": [128, 128, 128],
    "245": [138, 138, 138],
    "246": [148, 148, 148],
    "247": [158, 158, 158],
    "248": [168, 168, 168],
    "249": [178, 178, 178],
    "250": [188, 188, 188],
    "251": [198, 198, 198],
    "252": [208, 208, 208],
    "253": [218, 218, 218],
    "254": [228, 228, 228],
    "255": [238, 238, 238],
}
