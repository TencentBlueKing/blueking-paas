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

package app

import (
	"os"

	"github.com/fatih/color"
	"github.com/spf13/cobra"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/account"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/config"
	cmdUtil "github.com/TencentBlueKing/blueking-paas/client/pkg/utils/cmd"
)

var appLongDesc = `
Deploy PaaS application using subcommands like "bkpaas-cli app deploy"
`

// NewCmd create application command
func NewCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:                   "app",
		Short:                 "Manage PaaS application",
		Long:                  appLongDesc,
		DisableFlagsInUseLine: true,
		PersistentPreRun: func(cmd *cobra.Command, args []string) {
			if !account.IsUserAuthorized(config.G.AccessToken) {
				color.Red("User unauthorized! Please use `bkpaas-cli login` to login")
				os.Exit(1)
			}
		},
		Run: cmdUtil.DefaultSubCmdRun(),
	}
	// 配置信息查看
	cmd.AddCommand(NewCmdGetInfo())
	// 蓝鲸应用部署
	cmd.AddCommand(NewCmdDeploy())
	// 查看蓝鲸应用部署历史
	cmd.AddCommand(NewCmdDeployHistory())

	return cmd
}
