# -*- coding: utf-8 -*-
from typing import List, Optional

from attr import define


@define
class ExecAction:
    command: List[str]


@define
class HTTPHeader:
    name: str
    value: str


@define
class HTTPGetAction:
    port: int
    host: Optional[str] = None
    path: Optional[str] = None
    httpHeaders: Optional[List[HTTPHeader]] = None
    scheme: Optional[str] = None


@define
class TCPSocketAction:
    port: int
    host: Optional[str] = None
