/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *	http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

package cmd

import (
	"os"

	"github.com/spf13/cobra"

	"github.com/TencentBlueKing/blueking-paas/client/cmd/app"
	"github.com/TencentBlueKing/blueking-paas/client/cmd/config"
	"github.com/TencentBlueKing/blueking-paas/client/cmd/login"
	"github.com/TencentBlueKing/blueking-paas/client/cmd/version"
	cliConf "github.com/TencentBlueKing/blueking-paas/client/pkg/config"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/utils/logx"
)

// NewRootCmd ...
func NewRootCmd() *cobra.Command {
	var debug bool

	rootCmd := &cobra.Command{
		Use: "bkpaas-cli",
		Run: func(cmd *cobra.Command, args []string) {
			logx.Info("Hello %s, welcome to use bkpaas-cli, use `bkpaas-cli -h` for help", cliConf.G.Username)
		},
		PersistentPreRun: func(cmd *cobra.Command, args []string) {
			if debug {
				cliConf.EnableDebugMode()
			}
		},
	}

	// 用户登录
	rootCmd.AddCommand(login.NewCmd())
	// Cli 配置管理
	rootCmd.AddCommand(config.NewCmd())
	// 应用信息查询 / 部署
	rootCmd.AddCommand(app.NewCmd())
	// 版本信息
	rootCmd.AddCommand(version.NewCmd())

	// 允许通过指定 debug 参数开启调试模式
	rootCmd.PersistentFlags().BoolVar(&debug, "debug", false, "Enable debug mode")

	return rootCmd
}

// Execute bkpaas-cli command
func Execute() {
	if err := NewRootCmd().Execute(); err != nil {
		logx.Error("Failed to init root command: %s", err.Error())
		os.Exit(1)
	}
}
