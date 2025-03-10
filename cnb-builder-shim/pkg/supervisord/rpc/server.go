/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *     http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

package rpc

import (
	"context"
	"os/exec"
	"time"
)

// Server 是 supervisord 服务端
type Server struct {
	config ServerConfig
}

// ServerConfig 服务端配置
type ServerConfig struct {
	ConfigPath string // Supervisord 启动配置路径
}

// NewServer 用于创建一个新的 Supervisord Server
func NewServer(configPath string) *Server {
	return &Server{config: ServerConfig{ConfigPath: configPath}}
}

// Start 使用 command 显式启动 Supervisord Server
func (s *Server) Start() error {
	if s.isRunning() {
		return nil
	}
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, "supervisord", "-c", s.config.ConfigPath)
	if err := cmd.Run(); err != nil {
		return err
	}
	return nil
}

func (s *Server) isRunning() bool {
	// 使用 pgrep 检查 supervisord 进程
	cmd := exec.Command("pgrep", "-f", "supervisord")
	if err := cmd.Run(); err == nil {
		// 如果命令成功执行，说明 supervisord 已运行
		return true
	}

	// 如果命令执行失败，说明 supervisord 未运行
	return false
}
