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

// Package config provide command to manage bkpaas-cli config
package config

import (
	"github.com/spf13/cobra"

	cmdUtil "github.com/TencentBlueKing/blueking-paas/client/pkg/utils/cmd"
)

var configLongDesc = `
Display bkpaas-cli config files using subcommands like "bkpaas-cli config view"

The loading order follows these rules:
	
  1.  ${BKPAAS_CLI_CONFIG} environment variable.
  2.  Use ${HOME}/.blueking-paas/config.yaml.
`

// NewCmd create bkpaas-cli config command
func NewCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:                   "config",
		Short:                 "Manage bkpaas-cli config",
		Long:                  configLongDesc,
		DisableFlagsInUseLine: true,
		Run:                   cmdUtil.DefaultSubCmdRun(),
		GroupID:               cmdUtil.GroupCore.ID,
	}

	cmdUtil.DisableAuthCheck(cmd)
	// 配置信息查看
	cmd.AddCommand(NewCmdView())
	return cmd
}
