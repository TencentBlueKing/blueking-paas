"""Replace injected credential values on the way out of the process.

The Shell capability strips credentials from the environment the model's subprocesses inherit,
so under normal operation nothing here has anything to mask. What makes a second layer worth
having is that the first one fails *silently*: add a credential key without listing it, or take
a harness upgrade that changes how the list is applied, and every test still passes while the
model can read the value. This is what would notice.

Applied to the durable, searchable surfaces -- the persisted AG-UI events, HTTP error bodies,
and the process log. Deliberately not to the live event stream; see
:mod:`app_spark_agent.ui_events`.

Two limits worth knowing before treating this as a control rather than a backstop:

- Only exact configured values match. A credential that has been transformed on the way out --
  re-encoded, truncated, or split across two strings -- passes through untouched.
- Values, not names. Masking ``APP_SPARK_AGENT_MODEL_API_KEY`` as a string would make the settings table
  and every log line about it unreadable while protecting nothing.
"""

from functools import lru_cache
from typing import Any, cast

from app_spark_agent import settings

SECRET_PLACEHOLDER = "***"


@lru_cache(maxsize=8)
def _ordered(configured: tuple[str | None, ...]) -> tuple[str, ...]:
    """Return the non-empty values of ``configured``, longest first.

    Ordering matters when one credential contains another -- masking the shorter one first
    would leave the remainder of the longer one in the output, which reads as a partial leak.

    Cached on the values themselves rather than on nothing, so :func:`secret_values` can keep
    reading the settings on every call without repeating the sort. A handful of entries is
    enough for one process; the extra slots absorb tests that patch the credentials.
    """
    return tuple(sorted({value for value in configured if value}, key=len, reverse=True))


def secret_values() -> tuple[str, ...]:
    """Return the configured credential values, longest first.

    The settings are read on call rather than captured at import: a tuple built once at import
    would keep masking the values from whichever environment happened to be present then, and
    tests patch the module.

    :return: Every non-empty credential value, sorted by descending length.
    """
    return _ordered(
        (
            settings.BK_AIDEV_ACCESS_TOKEN,
            settings.MODEL_API_KEY,
            settings.CONTROL_PLANE_TOKEN,
            settings.RUNTIME_TOKEN,
        )
    )


def mask_text(text: str) -> str:
    """Return ``text`` with every configured credential value replaced."""
    for secret in secret_values():
        text = text.replace(secret, SECRET_PLACEHOLDER)
    return text


def mask_payload(value: Any) -> Any:
    """Return ``value`` with every credential value inside it replaced.

    Walks dictionaries, lists, and tuples so a whole JSON document can be handed over without
    the caller knowing which field might hold model output or echoed request content.

    Values only. A credential arrives as a value everywhere this is used -- a validation error
    puts the rejected input under ``input`` and the schema's own field names under ``loc`` --
    so walking keys as well would only cost a pass over data that cannot hold one.

    :param value: Any JSON-shaped structure, or a scalar to pass through.
    :return: A structure of the same shape with credentials replaced.
    """
    match value:
        case str():
            return mask_text(value)
        case dict():
            mapping = cast("dict[Any, Any]", value)
            return {key: mask_payload(item) for key, item in mapping.items()}
        case list():
            items = cast("list[Any]", value)
            return [mask_payload(item) for item in items]
        case tuple():
            elements = cast("tuple[Any, ...]", value)
            return tuple(mask_payload(item) for item in elements)
        case _:
            return value
