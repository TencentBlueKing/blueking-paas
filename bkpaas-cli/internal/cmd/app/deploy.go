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

	"github.com/MakeNowJust/heredoc/v2"
	"github.com/pkg/errors"
	"github.com/spf13/cobra"
	"gopkg.in/yaml.v3"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/handler"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/helper"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/model"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/utils/console"
)

// NewCmdDeploy returns a Command instance for 'app deploy' sub command
func NewCmdDeploy() *cobra.Command {
	var appCode, appModule, appEnv, branch, filePath, tag string
	var noWatch bool

	cmd := cobra.Command{
		Use:   "deploy",
		Short: "Deploy PaaS application",
		PreRunE: func(cmd *cobra.Command, args []string) error {
			if appCode == "" {
				_ = cmd.MarkFlagRequired("bk-app-code")
			}
			return nil
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			console.Info("Application %s deploying...", appCode)
			if err := deployApp(appCode, appModule, appEnv, branch, filePath, tag); err != nil {
				return errors.Wrapf(err, "Failed to deploy application %s", appCode)
			}
			if noWatch {
				return nil
			}
			// TODO 添加超时机制?
			// TODO 轮询体验优化，比如支持滚动更新日志？
			for {
				console.Info("Waiting for deploy finished...")
				time.Sleep(5 * time.Second)

				result, err := getDeployResult(appCode, appModule, appEnv)
				if err != nil {
					return errors.Wrapf(err, "failed to get app %s deploy result", appCode)
				}
				// 到达稳定状态后输出部署结果
				if result.IsStable() {
					fmt.Println(result)
					return nil
				}
			}
		},
	}

	cmd.Flags().StringVar(&appCode, "bk-app-code", "", "App ID (bk_app_code)")
	cmd.Flags().StringVar(&appCode, "code", "", heredoc.Doc(`
			[deprecated] App ID (bk_app_code)
			this will be removed in the future, please use --bk-app-code instead.`,
	))
	cmd.Flags().StringVar(&appModule, "module", "default", "module name")
	cmd.Flags().StringVar(&appEnv, "env", "stag", "environment (stag/prod)")
	cmd.Flags().StringVar(&branch, "branch", "", "git repo branch")
	cmd.Flags().StringVar(&tag, "tag", "", "image tag")
	cmd.Flags().StringVarP(&filePath, "file", "f", "", "bkapp manifest file path")
	cmd.Flags().BoolVar(&noWatch, "no-watch", false, "watch deploy process")
	return &cmd
}

// 应用部署
func deployApp(appCode, appModule, appEnv, branch, filePath, tag string) error {
	appType := helper.FetchAppType(appCode)

	opts := model.DeployOptions{
		AppCode:   appCode,
		AppType:   appType,
		Module:    appModule,
		DeployEnv: appEnv,
		Branch:    branch,
		Tag:       tag,
	}

	// TODO 参数检查是不是可以作为 DeployOptions 的方法？
	// 参数检查，普通应用需要指定部署的分支，云原生应用需要指定 manifest 文件路径
	if appType == model.AppTypeDefault && branch == "" {
		return errors.New("branch is required when deploy default app")
	}

	// 加载文件中的 bkapp manifest 内容
	if appType == model.AppTypeCNative && filePath != "" {
		yamlFile, err := os.ReadFile(filePath)
		if err != nil {
			return errors.Wrap(err, "failed to load bkapp manifest")
		}
		manifest := map[string]any{}
		if err = yaml.Unmarshal(yamlFile, &manifest); err != nil {
			return errors.Wrap(err, "failed to load bkapp manifest")
		}
		opts.BkAppManifest = manifest
	}

	if appType == model.AppTypeCNative && filePath == "" && tag == "" && branch == "" {
		return errors.New("manifest、tag or branch is required when deploy cloud native app")
	}

	deployer, err := handler.NewAppDeployer(appCode)
	if err != nil {
		return err
	}

	return deployer.Deploy(opts)
}
