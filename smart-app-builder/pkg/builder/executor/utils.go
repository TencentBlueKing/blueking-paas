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

package executor

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/pkg/errors"
	"github.com/samber/lo"

	bcfg "github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/buildconfig"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/config"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/plan"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/utils"
)

// archiveSourceTarball 生成 Procfile 文件后写入 sourceDir, 并将其打包成 destTGZ 文件
func archiveSourceTarball(sourceDir, destTGZ string, procfile map[string]string) error {
	procfileContent := ""

	// heroku Procfile: https://devcenter.heroku.com/articles/procfile#procfile-format
	for procType, procCommand := range procfile {
		procfileContent += fmt.Sprintf("%s: %s\n", procType, procCommand)
	}

	procfilePath := filepath.Join(sourceDir, "Procfile")
	if err := os.WriteFile(procfilePath, []byte(procfileContent), 0o644); err != nil {
		return errors.Wrap(err, "writing Procfile")
	}

	if err := utils.ArchiveTGZ(context.Background(), sourceDir, destTGZ); err != nil {
		return errors.Wrap(err, "archive source code")
	}

	return nil
}

// archiveArtifactTarball 将 app_desc.yaml、logo、.Version 以及 artifact.json 写入 artifactDir,
// 再将目录打包成 {app_code}.tgz 并返回其路径.
// 注意：无论是 v1(旧方案) 还是 v2(新方案), 都会生成并写入 artifact.json 文件
func archiveArtifactTarball(buildPlan *plan.BuildPlan, artifactDir string) (string, error) {
	// 1. 将 app_desc.yaml, logo, .Version 写入 artifactDir
	appDescName := filepath.Base(buildPlan.AppDescPath)
	if err := utils.CopyFile(buildPlan.AppDescPath, filepath.Join(artifactDir, appDescName)); err != nil {
		return "", err
	}
	if buildPlan.LogoFilePath != "" {
		logoName := filepath.Base(buildPlan.LogoFilePath)
		if err := utils.CopyFile(buildPlan.LogoFilePath, filepath.Join(artifactDir, logoName)); err != nil {
			return "", err
		}
	}

	builderFlagPath := filepath.Join(artifactDir, ".Version")
	if err := os.WriteFile(builderFlagPath, []byte("cnb-image-layers"), 0o644); err != nil {
		return "", errors.Wrap(err, "writing builder flag .Version")
	}

	// 2. 生成并写入 `artifact.json` 到 artifactDir
	if err := writeArtifactJsonFile(buildPlan, artifactDir); err != nil {
		return "", errors.Wrap(err, "writing artifact.json")
	}

	// 3. 打包成 {app_code}.tgz
	artifactTGZ := filepath.Join(artifactDir, fmt.Sprintf("%s.tgz", buildPlan.AppCode))
	if err := utils.ArchiveTGZ(context.Background(), artifactDir, artifactTGZ); err != nil {
		return "", errors.Wrap(err, "archive artifact")
	}
	return artifactTGZ, nil
}

// makeRunArgs 生成运行命令, 其中 moduleSrcTGZ 为模块源码包, runImage 为运行时镜像
func makeRunArgs(appCode string, group *plan.ModuleBuildGroup, moduleSrcTGZ string, runImage string) []string {
	args := make([]string, 0)

	envSlice := lo.MapToSlice(group.Envs, func(k string, v string) string {
		return fmt.Sprintf("%s=%s", k, v)
	})

	// 添加 buildpacks 环境变量
	for _, bp := range group.Buildpacks {
		envSlice = append(envSlice, bcfg.GetBuildpacksEnvs(bp.Name)...)
	}

	bindTarget := "/tmp/source.tgz"
	envSlice = append(
		envSlice,
		[]string{
			fmt.Sprintf("REQUIRED_BUILDPACKS=%s", group.RequiredBuildpacks),
			fmt.Sprintf("OUTPUT_IMAGE=%s", group.OutputImage),
			fmt.Sprintf("CNB_RUN_IMAGE=%s", runImage),
			fmt.Sprintf("SOURCE_GET_URL=file://%s", bindTarget),
			"USE_DOCKER_DAEMON=true",
			"CNB_PLATFORM_API=0.11",
		}...)

	for _, env := range envSlice {
		args = append(args, "-e", env)
	}

	// 添加缓存配置
	if config.G.CacheRegistry != "" {
		cacheImage := fmt.Sprintf("%s/%s/%s:cnb-build-cache", config.G.CacheRegistry, appCode, group.BuildModuleName)
		args = append(args, "-e", fmt.Sprintf("CACHE_IMAGE=%s", cacheImage))
		if config.G.RegistryAuth != "" {
			args = append(args, "-e", fmt.Sprintf("CNB_REGISTRY_AUTH=%s", config.G.RegistryAuth))
		}
	}

	// 挂载源码压缩包
	args = append(args, "--mount", fmt.Sprintf("type=bind,source=%s,target=%s", moduleSrcTGZ, bindTarget))

	args = append(
		args,
		"--mount",
		fmt.Sprintf("type=bind,source=%s,target=/var/run/docker.sock", config.G.DaemonSockFile),
	)

	return args
}

// writeArtifactJsonFile 根据 buildPlan 在 artifactDir 写入 artifact.json
// 输出的 artifact.json 格式示例:
//
//	{
//	  "version": "1.0",
//	  "runtime": {"base_image_id": "default", "architecture": "amd64"},
//	  "app_artifacts": {
//	    "module1": {"image_tar": "module1.tar", "proc_entrypoints": {"web": ["module1-web"]}},
//	    "module2": {"image_tar": "module2.tar", "proc_entrypoints": {"api": ["module2-api"]}}
//	  }
//	}
func writeArtifactJsonFile(buildPlan *plan.BuildPlan, artifactDir string) error {
	moduleArtifact := make(map[string]map[string]any)
	for _, group := range buildPlan.BuildGroups {
		for _, name := range group.ModuleNames {
			moduleArtifact[name] = map[string]any{"image_tar": group.OutputImageTarName}
		}
	}

	for moduleName, procInfo := range buildPlan.ProcessCommands {
		entrypoints := make(map[string][]string)
		for procName := range procInfo {
			entrypoints[procName] = []string{plan.GenerateProcType(moduleName, procName)}
		}
		moduleArtifact[moduleName]["proc_entrypoints"] = entrypoints
	}

	// Build the new artifact.json structure with version, runtime and app_artifacts
	artifact := map[string]any{
		"version": "1.0",
		"runtime": map[string]string{
			"base_image_id": buildPlan.BaseImageID,
			"architecture":  buildPlan.Architecture,
		},
		"app_artifacts": moduleArtifact,
	}

	relBytes, err := json.Marshal(artifact)
	if err != nil {
		return err
	}
	if err = os.WriteFile(filepath.Join(artifactDir, "artifact.json"), relBytes, 0o644); err != nil {
		return err
	}
	return nil
}
