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
)

// OpTypeView 操作类型：查看
const OpTypeView = "config"

// OpTypeDeploy 操作类型：部署
const OpTypeDeploy = "deploy"

var appCode, appModule, appEnv string

// NewCmd create application command
func NewCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "app",
		Short: "Manage PaaSv3 application",
		PreRun: func(cmd *cobra.Command, args []string) {
			// check user is authenticated
			if !account.IsUserAuthorized() {
				color.Red("User unauthorized! Please use `bkpaas-cli login` to login")
				os.Exit(1)
			}
		},
		Run: func(cmd *cobra.Command, args []string) {
			// TODO 重构，做子命令改造，不再使用 args 区分操作
			if len(args) == 0 {
				color.Red("operator kind (%s / %s) is required", OpTypeView, OpTypeDeploy)
			}
			switch args[0] {
			case OpTypeView:
				displayAppInfo(appCode, appModule, appEnv)
			case OpTypeDeploy:
				deployApp()
			default:
				color.Red("unknown operator type: (%s)", args[0])
			}
		},
	}

	// flag 解析
	cmd.Flags().StringVarP(&appCode, "code", "", "", "app code")
	cmd.Flags().StringVarP(&appModule, "module", "", "default", "module name")
	cmd.Flags().StringVarP(&appEnv, "env", "", "prod", "environment (stag/prod)")
	// 必须指定 appCode
	_ = cmd.MarkFlagRequired("code")
	return cmd
}
