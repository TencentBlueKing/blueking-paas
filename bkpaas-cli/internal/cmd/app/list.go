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

// NewCmdList returns a Command instance for 'app list' sub command
func NewCmdList() *cobra.Command {
	return &cobra.Command{
		Use:   "list",
		Short: "List PaaS applications",
		Long: heredoc.Doc(`
        查看你有操作权限的蓝鲸应用.
        `),
		Example: heredoc.Doc(`
		>>> bkpaas-cli app list
		
		Application List
		+----+------------------+------------------+
		| #  |      NAME        |       CODE       |
		+----+------------------+------------------+
		|  1 | demo-app-1       | app-code-1       |
		|  2 | demo-app-2       | app-code-2       |
		|  3 | demo-app-3       | app-code-3       |
		+----+------------------+------------------+
        `),
		RunE: func(cmd *cobra.Command, args []string) error {
			return listApps()
		},
	}
}

// 在命令行中展示当前用户有权限的应用列表
func listApps() error {
	applications, err := handler.NewAppLister().Exec()
	if err != nil {
		return errors.Wrap(err, "Failed to list applications")
	}
	fmt.Println(applications)
	return nil
}
