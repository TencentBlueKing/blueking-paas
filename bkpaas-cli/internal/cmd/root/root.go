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

// Package root is the root command of bkpaas-cli
package root

import (
	"os"

	"github.com/pkg/errors"
	"github.com/spf13/cobra"

	"github.com/TencentBlueKing/blueking-paas/client/internal/cmd/app"
	"github.com/TencentBlueKing/blueking-paas/client/internal/cmd/config"
	"github.com/TencentBlueKing/blueking-paas/client/internal/cmd/login"
	"github.com/TencentBlueKing/blueking-paas/client/internal/cmd/version"
	cliConf "github.com/TencentBlueKing/blueking-paas/client/pkg/config"
	cmdutil "github.com/TencentBlueKing/blueking-paas/client/pkg/utils/cmd"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/utils/console"
)

// NewRootCmd ...
func NewRootCmd() *cobra.Command {
	var debug bool

	rootCmd := &cobra.Command{
		Use:   "bkpaas-cli",
		Short: "BK-PaaS Cli",
		Long:  "Work seamlessly with BK-PaaS from the command line.",
		Run: func(cmd *cobra.Command, args []string) {
			console.Info("Hello %s, welcome to use bkpaas-cli, use `bkpaas-cli -h` for help", cliConf.G.Username)
		},
		PersistentPreRunE: func(cmd *cobra.Command, args []string) error {
			if debug {
				cliConf.EnableDebugMode()
			}
			// load global config ...
			if _, err := cliConf.LoadConf(cliConf.FilePath); err != nil {
				console.Tips("Please follow the user guide (Readme.md) to initialize the configuration...")
				return errors.Wrap(err, "Failed to load config")
			}

			// require that the user is authenticated before running most commands
			if cmdutil.IsAuthRequired(cmd) && !cmdutil.CheckAuth(cliConf.G) {
				return errors.New("User unauthorized! Please use `bkpaas-cli login` to login")
			}
			return nil
		},
	}
	cmdutil.DisableAuthCheck(rootCmd)

	rootCmd.AddGroup(&cmdutil.GroupCore)

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
		console.Error(err.Error())
		os.Exit(1)
	}
}
