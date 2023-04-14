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
	"os"
	"time"

	"github.com/fatih/color"
	"github.com/pkg/errors"
	"github.com/spf13/cobra"
	"gopkg.in/yaml.v3"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/handler"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/helper"
)

// NewCmdDeploy returns a Command instance for 'app deploy' sub command
func NewCmdDeploy() *cobra.Command {
	var appCode, appModule, appEnv, branch, filePath string
	var showResponse, noWatch bool

	cmd := cobra.Command{
		Use:   "deploy",
		Short: "Deploy PaaS application",
		Run: func(cmd *cobra.Command, args []string) {
			fmt.Printf("Application %s deploying...\n", appCode)
			respData, err := deployApp(appCode, appModule, appEnv, branch, filePath)
			if showResponse {
				fmt.Println("Deploy API Response Data:", respData)
			}
			if err != nil {
				color.Red(fmt.Sprintf("failed to deploy application %s, error: %s", appCode, err.Error()))
				os.Exit(1)
			}
			if noWatch {
				return
			}
			// TODO 添加超时机制 15min
			for {
				fmt.Println("Waiting for deploy finish...")
				time.Sleep(5 * time.Second)

				result, err := getDeployResult(appCode, appModule, appEnv)
				if err != nil {
					color.Red(fmt.Sprintf("failed to get app %s deploy result, error: %s", appCode, err.Error()))
					os.Exit(1)
				}
				// 到达稳定状态后输出部署结果
				// TODO 部署成功/失败后，弹出页面链接，方便用户快捷前往开发者中心
				if result.IsStable() {
					fmt.Println(result)
					return
				}
			}
		},
	}

	cmd.Flags().StringVar(&appCode, "code", "", "app code")
	cmd.Flags().StringVar(&appModule, "module", "default", "module name")
	cmd.Flags().StringVar(&appEnv, "env", "stag", "environment (stag/prod)")
	cmd.Flags().StringVar(&branch, "branch", "", "git repo branch")
	cmd.Flags().StringVarP(&filePath, "file", "f", "", "bkapp manifest file path")
	cmd.Flags().BoolVar(&showResponse, "show-resp", false, "show deploy api response")
	cmd.Flags().BoolVar(&noWatch, "no-watch", false, "watch deploy process")
	_ = cmd.MarkFlagRequired("code")

	return &cmd
}

// 应用部署
func deployApp(appCode, appModule, appEnv, branch, filePath string) (map[string]any, error) {
	appType := helper.FetchAppType(appCode)

	opts := handler.DeployOptions{
		AppCode:   appCode,
		AppType:   appType,
		Module:    appModule,
		DeployEnv: appEnv,
		Branch:    branch,
	}

	// 参数检查，普通应用需要指定部署的分支，云原生应用需要指定 manifest 文件路径
	if appType == handler.AppTypeDefault && branch == "" {
		return nil, errors.New("branch is required when deploy default app")
	}

	// 加载文件中的 bkapp manifest 内容
	if appType == handler.AppTypeCNative {
		if filePath == "" {
			return nil, errors.New("manifest file path is required when deploy cnative app")
		}
		yamlFile, err := os.ReadFile(filePath)
		if err != nil {
			return nil, errors.Wrap(err, "failed to load bkapp manifest")
		}
		manifest := map[string]any{}
		if err = yaml.Unmarshal(yamlFile, &manifest); err != nil {
			return nil, errors.Wrap(err, "failed to load bkapp manifest")
		}
		opts.BkAppManifest = manifest
	}

	deployer, err := handler.NewAppDeployer(appCode)
	if err != nil {
		return nil, err
	}

	return deployer.Exec(opts)
}
