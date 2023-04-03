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
	"github.com/spf13/cobra"

	cmdUtil "github.com/TencentBlueKing/blueking-paas/client/pkg/utils/cmd"
)

var appCode, appModule, appEnv string

var appLongDesc = `
Deploy PaasV3 application using subcommands like "bkpaas-cli app deploy"

TODO 补充描述内容
`

// NewCmd create application command
func NewCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:                   "app",
		Short:                 "Manage PaaSv3 application",
		Long:                  appLongDesc,
		DisableFlagsInUseLine: true,
		Run:                   cmdUtil.DefaultSubCmdRun(),
	}
	// 配置信息查看
	cmd.AddCommand(NewCmdView())
	// 蓝鲸应用部署
	cmd.AddCommand(NewCmdDeploy())

	// flag 解析 TODO 确认 flags 继承情况
	cmd.Flags().StringVarP(&appCode, "code", "", "", "app code")
	cmd.Flags().StringVarP(&appModule, "module", "", "default", "module name")
	cmd.Flags().StringVarP(&appEnv, "env", "", "prod", "environment (stag/prod)")
	// 必须指定 appCode
	_ = cmd.MarkFlagRequired("code")
	return cmd
}
