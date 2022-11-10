# -*- coding: utf-8 -*-
from collections import OrderedDict
from typing import TYPE_CHECKING, Dict, Optional, Type

from .v1 import V1Mapper
from .v2 import V2Mapper

if TYPE_CHECKING:
    from .mapper import MapperPack

# 按照 version 添加的顺序
AVAILABLE_GENERATIONS: Dict[str, Type['MapperPack']] = OrderedDict(v1=V1Mapper, v2=V2Mapper)


def get_mapper_version(target: str, init_kwargs: Optional[dict] = None):
    available_packs = dict()
    for generation, mapper_class in AVAILABLE_GENERATIONS.items():
        available_packs[generation] = mapper_class(**init_kwargs or {})
    return available_packs[target]


def get_latest_mapper_version(init_kwargs: Optional[dict] = None):
    """获取最新的 mapper version"""
    target = list(AVAILABLE_GENERATIONS.keys())[-1]
    return AVAILABLE_GENERATIONS[target](**init_kwargs or {})


def check_if_available(target: str):
    """
    :exception ValueError: 当 target 不在可用列表中时抛出
    :param target:  目标版本，例如 v1, v2
    :return: None
    """
    if target not in AVAILABLE_GENERATIONS:
        raise ValueError("%s is not available, please choose version in %s", target, AVAILABLE_GENERATIONS.keys())
