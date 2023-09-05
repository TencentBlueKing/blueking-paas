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
)

// NewCmdGetInfo returns a Command instance for 'app get-info' sub command
func NewCmdGetInfo() *cobra.Command {
	var appCode string

	cmd := cobra.Command{
		Use:   "get-info",
		Short: "Get PaaS application info",
		PreRunE: func(cmd *cobra.Command, args []string) error {
			if appCode == "" {
				_ = cmd.MarkFlagRequired("bk-app-code")
			}
			return nil
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			return displayAppInfo(appCode)
		},
	}

	cmd.Flags().StringVar(&appCode, "bk-app-code", "", "App ID (bk_app_code)")
	cmd.Flags().StringVar(&appCode, "code", "", heredoc.Doc(`
			[deprecated] App ID (bk_app_code)
			this will be removed in the future, please use --bk-app-code instead.`,
	))
	return &cmd
}

// 在命令行中展示指定的蓝鲸应用信息
func displayAppInfo(appCode string) error {
	retriever := handler.NewBasicInfoRetriever()
	appInfo, err := retriever.Exec(appCode)
	if err != nil {
		return errors.Wrap(err, "Failed to get application info")
	}
	fmt.Println(appInfo)
	return nil
}
