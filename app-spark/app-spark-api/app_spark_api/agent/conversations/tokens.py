# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

"""How an Agent Runtime proves which conversation it is allowed to write state for.

A signed value rather than a stored one: the only facts that need carrying are the conversation
id and the epoch below, this service's ``SECRET_KEY`` is enough to make them unforgeable, and a
token table would add a row to write on every spawn and clean up on every teardown for no gain.

Deliberately without an expiry. A Runtime is a long-lived process that may sit idle between
turns for as long as its user keeps the tab open, and a token that expired underneath it would
turn a paused conversation into lost conversation state.

So revocation is explicit instead of timed, and that is what the epoch is for. A token names the
epoch it was minted under, and the ingest endpoints refuse anything that does not match the
conversation's current one -- which costs no extra query there, since the row is loaded to
authorize the write anyway. Bumping it cuts off every token issued so far, including one held by
a Runtime this service has lost track of but that is still running and still able to write.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import attrs
from django.core import signing

if TYPE_CHECKING:
    from uuid import UUID

# Namespaces the signature, so a token minted here cannot be replayed against any other signed
# value this service happens to produce.
TOKEN_SALT = "app_spark_api.agent.conversations.state"


class InvalidStateToken(Exception):
    """Raised when a state-ingest token is missing, malformed, or not correctly signed."""


@attrs.frozen
class StateTokenClaims:
    """What a verified state-ingest token asserts.

    Neither field is trusted on its own: the caller checks the conversation against the one in
    the request path, and the epoch against the one on the row.

    :param conversation_id: Conversation the token was minted for, as a string.
    :param epoch: Revocation generation the token was minted under.
    """

    conversation_id: str
    epoch: int


def mint_state_token(conversation_id: UUID, *, epoch: int) -> str:
    """Return the token a Runtime serving ``conversation_id`` writes state with.

    :param conversation_id: Conversation the token authorizes writes to, and only that one.
    :param epoch: The conversation's current ``state_epoch``. A token minted under an earlier
        one has been revoked and will be refused.
    :return: An opaque token safe to hand to the Runtime process.
    """
    return signing.Signer(salt=TOKEN_SALT).sign(f"{conversation_id}:{epoch}")


def read_state_token(token: str) -> StateTokenClaims:
    """Return what ``token`` asserts, having checked its signature.

    :param token: Token as the Runtime presented it.
    :return: The claims; callers compare them with the conversation they were asked about
        rather than trusting the request's own path.
    :raises InvalidStateToken: If the token is empty, malformed, or not correctly signed.
    """
    if not token:
        raise InvalidStateToken("no state token was presented")
    try:
        value = signing.Signer(salt=TOKEN_SALT).unsign(token)
    except signing.BadSignature as exc:
        raise InvalidStateToken("the state token is not correctly signed") from exc

    # Partitioned from the right: `Signer` itself separates value from signature on the last
    # colon, so the epoch is the only field that can be read off the end unambiguously.
    conversation_id, separator, raw_epoch = value.rpartition(":")
    if not separator:
        raise InvalidStateToken("the state token does not name an epoch")
    try:
        epoch = int(raw_epoch)
    except ValueError as exc:
        raise InvalidStateToken("the state token's epoch is not an integer") from exc
    return StateTokenClaims(conversation_id=conversation_id, epoch=epoch)
