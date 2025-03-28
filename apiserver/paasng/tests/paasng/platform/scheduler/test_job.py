# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from paasng.core.tenant.user import OP_TYPE_TENANT_ID
from paasng.platform.scheduler.jobs import init_service_default_policy_job, logger, redis_lock


@pytest.fixture
def mock_redis_lock():
    with patch("paasng.platform.scheduler.jobs.redis_lock") as mock:
        yield mock


@pytest.fixture
def mock_service():
    service = MagicMock()
    service.uuid = "test-service-uuid"
    service.name = "test-service"
    return service


@pytest.fixture
def mock_service_list(mock_service):
    with patch("paasng.platform.scheduler.jobs.mixed_service_mgr.list") as mock:
        mock.return_value = [mock_service]
        yield mock


class TestInitServiceDefaultPolicyJob:
    @override_settings(ENABLE_MULTI_TENANT_MODE=True)
    def test_lock_acquired_success(self, mock_redis_lock, mock_service_list, mock_service):
        # 模拟成功获取锁
        mock_lock = MagicMock()
        mock_lock.__enter__.return_value = True
        mock_redis_lock.return_value = mock_lock

        with patch(
            "paasng.platform.scheduler.jobs._handel_single_service_default_policy"
        ) as mock_handler, patch.object(logger, "info") as mock_info_log:
            init_service_default_policy_job()

            # 验证锁参数
            mock_redis_lock.assert_called_once_with("lock:init_service_default_policy")
            # 验证处理逻辑被调用
            mock_handler.assert_called_once_with(mock_service, OP_TYPE_TENANT_ID)
            # 验证日志
            mock_info_log.assert_any_call("Starting service policy initialization process.")
            mock_info_log.assert_any_call("Service policy initialization completed.")

    def test_lock_not_acquired_skip(self, mock_redis_lock, mock_service_list):
        # 模拟未获取锁
        mock_lock = MagicMock()
        mock_lock.__enter__.return_value = False
        mock_redis_lock.return_value = mock_lock

        with patch(
            "paasng.platform.scheduler.jobs._handel_single_service_default_policy"
        ) as mock_handler, patch.object(logger, "info") as mock_debug_log:
            init_service_default_policy_job()

            # 验证处理逻辑未被调用
            mock_handler.assert_not_called()
            # 验证跳过日志
            mock_debug_log.assert_called_with("Another instance is handling service policy initialization, skip.")

    def test_lock_release_guarantee(self, mock_redis_lock, mock_service_list):
        # 测试异常情况下锁仍然会被释放
        mock_lock = MagicMock()
        mock_lock.__enter__.return_value = True
        mock_redis_lock.return_value = mock_lock

        with patch(
            "paasng.platform.scheduler.jobs._handel_single_service_default_policy",
            side_effect=RuntimeError("Simulated policy initialization error"),
        ):
            with pytest.raises(RuntimeError, match="Simulated policy initialization error"):
                init_service_default_policy_job()

            # 验证锁释放逻辑
            mock_lock.__exit__.assert_called_once()

    def test_lock_normal_release(self):
        """测试锁正常获取和释放流程"""
        mock_redis = MagicMock()
        mock_redis.lock.return_value = MagicMock(acquire=MagicMock(return_value=True), release=MagicMock())

        # 使用真实上下文管理器逻辑
        with patch("paasng.platform.scheduler.jobs.get_default_redis", return_value=mock_redis):
            lock_key = "test:normal:lock"
            with redis_lock(lock_key) as acquired:
                # 验证成功获取锁
                assert acquired is True
                # 验证锁参数设置正确
                mock_redis.lock.assert_called_once_with(
                    name=lock_key, timeout=300, blocking_timeout=0, thread_local=False
                )

            # 验证锁释放
            mock_redis.lock.return_value.release.assert_called_once()
