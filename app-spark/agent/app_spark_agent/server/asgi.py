"""ASGI entry point for an external server."""

from app_spark_agent.server.app import create_app_from_settings

app = create_app_from_settings()
