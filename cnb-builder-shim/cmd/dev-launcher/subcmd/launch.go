/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *     http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

package subcmd

import (
	"os"
	"path/filepath"
	"strings"

	"github.com/BurntSushi/toml"
	"github.com/buildpacks/lifecycle/launch"
	"github.com/spf13/cobra"

	devlaunch "github.com/TencentBlueking/bkpaas/cnb-builder-shim/cmd/dev-launcher/launch"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/appdesc"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/logging"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/utils"
)

var DefaultAppDir = utils.EnvOrDefault("CNB_APP_DIR", "/app")

var reloadCmd = &cobra.Command{
	Use:   "reload",
	Short: "reload processes.",
	Long:  "reload the given launch.Process list.",
	RunE: func(cmd *cobra.Command, args []string) error {
		logger := logging.Default()

		// 从当前进程环境变量中获取（即 Relaunch 中设置的 cmd.Env）
		envList := make([]appdesc.Env, 0)
		for _, envStr := range os.Environ() {
			// 分割 "KEY=VALUE" 格式的环境变量
			parts := strings.SplitN(envStr, "=", 2)
			if len(parts) == 2 {
				envList = append(envList, appdesc.Env{
					Name:  parts[0],
					Value: parts[1],
				})
			}
		}

		var md launch.Metadata

		if _, err := toml.DecodeFile(launch.GetMetadataFilePath("/layers"), &md); err != nil {
			logger.Error(err, "read metadata")
			return err
		}

		appDesc, err := appdesc.UnmarshalToAppDesc(filepath.Join(DefaultAppDir, "app_desc.yaml"))
		if err != nil {
			logger.Error(err, "parse invalid app_desc.yaml")
			return err
		}

		// 合并环境变量到 appDesc
		if len(envList) > 0 {
			appdesc.MergeEnvVars(appDesc, envList)
		}

		if err = devlaunch.Run(md.Processes, appDesc); err != nil {
			logger.Error(err, "failed to hot launch")
			return err
		}
		return nil
	},
}

func init() {
	rootCmd.AddCommand(reloadCmd)
}
