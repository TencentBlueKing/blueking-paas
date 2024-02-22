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
	"fmt"

	"github.com/MakeNowJust/heredoc/v2"
	"github.com/pkg/errors"
	"github.com/spf13/cobra"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/handler"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/model"
)

// NewCmdDeployHistory returns a Command instance for 'app deploy-history' sub command
func NewCmdDeployHistory() *cobra.Command {
	var appCode, appModule, appEnv string

	cmd := cobra.Command{
		Use:   "deploy-history",
		Short: "List PaaS application deploy history",
		PreRunE: func(cmd *cobra.Command, args []string) error {
			if appCode == "" {
				_ = cmd.MarkFlagRequired("bk-app-code")
			}
			return nil
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			return errors.New("the feature is currently unavailable")

			history, err := listDeployHistory(appCode, appModule, appEnv)
			if err != nil {
				return errors.Wrapf(err, "Failed to list application %s deploy history", appCode)
			}
			fmt.Println(history)
			return nil
		},
	}

	cmd.Flags().StringVar(&appCode, "bk-app-code", "", "App ID (bk_app_code)")
	cmd.Flags().StringVar(&appCode, "code", "", heredoc.Doc(`
			[deprecated] App ID (bk_app_code)
			this will be removed in the future, please use --bk-app-code instead.`,
	))
	cmd.Flags().StringVar(&appModule, "module", "default", "module name")
	cmd.Flags().StringVar(&appEnv, "env", "stag", "environment (stag/prod)")
	return &cmd
}

// 获取应用部署历史
func listDeployHistory(appCode, appModule, appEnv string) (model.DeployHistory, error) {
	opts := model.DeployOptions{
		AppCode:   appCode,
		Module:    appModule,
		DeployEnv: appEnv,
	}

	deployer, err := handler.NewAppDeployer(appCode)
	if err != nil {
		return nil, err
	}
	return deployer.GetHistory(opts)
}
