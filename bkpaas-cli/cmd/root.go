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
	"fmt"
	"os"

	"github.com/fatih/color"
	"github.com/spf13/cobra"

	"github.com/TencentBlueKing/blueking-paas/client/cmd/app"
	"github.com/TencentBlueKing/blueking-paas/client/cmd/config"
	"github.com/TencentBlueKing/blueking-paas/client/cmd/login"
	"github.com/TencentBlueKing/blueking-paas/client/cmd/version"
	cliConf "github.com/TencentBlueKing/blueking-paas/client/pkg/config"
)

// NewRootCmd ...
func NewRootCmd() *cobra.Command {
	rootCmd := &cobra.Command{
		Use: "bkpaas-cli",
		Run: func(cmd *cobra.Command, args []string) {
			fmt.Printf("Hello %s, welcome to use bkpaas-cli, use `bkpaas-cli -h` for help\n", cliConf.G.Username)
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

	return rootCmd
}

// Execute bkpaas-cli command
func Execute() {
	if err := NewRootCmd().Execute(); err != nil {
		color.Red(err.Error())
		os.Exit(1)
	}
}
