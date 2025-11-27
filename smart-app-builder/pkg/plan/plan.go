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

// Package plan ...
package plan

import (
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"strings"

	"github.com/pkg/errors"
	"golang.org/x/exp/maps"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/appdesc"
	bcfg "github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/buildconfig"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/config"
)

const AppDescFileName = "app_desc.yaml"

// BuildPlan 定义了应用的构建方案, 包含所有模块的构建配置分组.
// 注意：BuildPlan 同时支持两种打包方案(由 `PackagingVersion` 控制):
//   - v2(新方案，默认): 采用“构建组”概念. 采用相同构建方案的模块会合并到同一构建组, 复用同一份构建产物(image tar)
//     相同构建方案判定标准：
//     1. 代码目录相同
//     2. 构建语言或 buildpacks 相同
//   - v1(旧方案): 不做模块合并, 每个模块单独构建并输出其各自的 artifact (每个模块视为独立的构建组/单元)
type BuildPlan struct {
	// AppCode 应用 code
	AppCode string
	// AppDescPath 应用描述文件路径
	AppDescPath string
	// LogoFilePath 应用 Logo 文件路径
	LogoFilePath string
	// ProcessCommands 模块各进程及其启动命令
	// 格式: {"模块名":{"进程名":"启动命令"}}
	ProcessCommands map[string]map[string]string
	// BuildGroups 模块构建组列表
	BuildGroups []*ModuleBuildGroup
	// PackagingVersion 打包方案版本 (v1: 旧方案, v2: 新方案)
	PackagingVersion string
}

// GenerateProcfile 生成 Procfile (进程名 -> 启动命令) 的映射关系
// 返回值示例: "web-web-process": "python main.py" (v2) 或 "web": "python main.py" (v1)
// 使用说明:
//   - v2 (默认): 返回应用范围的统一 Procfile, key 为 "模块名-进程名"; 函数的 moduleName 参数将被忽略
//   - v1 (旧方案): 返回指定模块 (moduleName) 的 Procfile, key 为进程名; 如果指定模块不存在, 则返回空 map
func (b *BuildPlan) GenerateProcfile(moduleName string) map[string]string {
	// 兜底操作, moduleName 不可为空串
	if moduleName == "" {
		panic("moduleName must be provided.")
	}

	procfile := make(map[string]string)

	// v1: 返回指定模块的 Procfile(moduleName 必须提供)
	if b.PackagingVersion == "v1" {
		if procInfo, ok := b.ProcessCommands[moduleName]; ok {
			for processName, procCommand := range procInfo {
				procfile[processName] = procCommand
			}
		}
		return procfile
	}

	// v2: 与模块无关, 返回整个应用的统一 Procfile, key 为 "模块名-进程名"
	for moduleName, procInfo := range b.ProcessCommands {
		for processName, procCommand := range procInfo {
			procfile[GenerateProcType(moduleName, processName)] = procCommand
		}
	}

	return procfile
}

// ModuleBuildGroup 是共享相同构建配置的模块分组, 组内所有模块复用同一个构建流程(仅构建一次)和输出镜像
// 在 v2 方案中, 这是真正的"合并"单位;
// 在 v1 方案中, 每个 ModuleBuildGroup 仅包含单个模块(等价于每模块独立构建)
type ModuleBuildGroup struct {
	// SourceDir 是 app_desc.yaml 中模块的代码路径(相对路径)
	SourceDir string
	// RequiredBuildpacks 格式如: tgz bk-buildpack-apt ... v2;tgz bk-buildpack-python ... v213
	RequiredBuildpacks string
	Buildpacks         []bcfg.Buildpack
	// BuildModuleName 是当前构建执行的目标模块名
	BuildModuleName string
	// ModuleNames 共享 OutputImage 的所有模块名（包含 BuildModuleName）
	ModuleNames []string
	// Envs 是当前构建所需要的环境变量
	Envs map[string]string
	// OutputImage 是当前构建出的镜像
	OutputImage string
	// OutputImageTarName 是当前构建出的镜像的压缩包名
	OutputImageTarName string
}

// PrepareBuildPlan 解析 app_desc.yaml 文件, 生成 BuildPlan
func PrepareBuildPlan(sourceDir string) (*BuildPlan, error) {
	if err := ensureAppDescYaml(sourceDir); err != nil {
		return nil, err
	}

	desc, err := appdesc.ParseAppDescYAML(filepath.Join(sourceDir, AppDescFileName))
	if err != nil {
		return nil, errors.Wrap(err, "parse app_desc.yaml")
	}

	if err = desc.Validate(); err != nil {
		return nil, err
	}

	procCommands := desc.GenerateProcessCommands()
	if len(procCommands) == 0 {
		return nil, errors.New("no valid processes found in app_desc.yaml")
	}

	groups, err := buildModuleBuildGroups(sourceDir, desc)
	if err != nil {
		return nil, err
	}

	plan := &BuildPlan{
		AppCode:          desc.GetAppCode(),
		AppDescPath:      filepath.Join(sourceDir, AppDescFileName),
		LogoFilePath:     detectLogoFile(sourceDir),
		ProcessCommands:  procCommands,
		BuildGroups:      groups,
		PackagingVersion: config.G.PackagingVersion,
	}

	return plan, nil
}

// ensureAppDescYaml 确保 app_desc.yaml 存在
func ensureAppDescYaml(sourceDir string) error {
	_, err := os.Stat(filepath.Join(sourceDir, AppDescFileName))
	// 如果 app_desc.yaml 不存在, 则尝试探测 app_desc.yml
	if err != nil && os.IsNotExist(err) {
		if _, err = os.Stat(filepath.Join(sourceDir, "app_desc.yml")); err != nil {
			return err
		}
		// 重命名为 app_desc.yaml
		return os.Rename(filepath.Join(sourceDir, "app_desc.yml"), filepath.Join(sourceDir, AppDescFileName))

	}
	return err
}

// buildModuleBuildGroups 生成模块构建组
func buildModuleBuildGroups(sourceDir string, desc appdesc.AppDesc) ([]*ModuleBuildGroup, error) {
	configs, err := desc.GenerateModuleBuildConfig()
	if err != nil {
		return nil, err
	}

	groupMap := make(map[string]*ModuleBuildGroup)

	for _, cfg := range configs {
		if aptfileExists(filepath.Join(sourceDir, cfg.SourceDir)) {
			bp, _ := bcfg.GetBuildpackByLanguage("apt")
			cfg.Buildpacks = append(cfg.Buildpacks, *bp)
		}

		rBuildpacks, err := ToRequiredBuildpacks(cfg.Buildpacks)
		if err != nil {
			return nil, err
		}

		// v1 (旧方案): 每个模块独立构建, 不共享镜像, 镜像文件使用 .tgz 后缀
		// v2 (新方案): 合并采用相同构建方案的模块, 镜像文件使用 .tar 后缀
		var k, imageTarExt string
		if config.G.PackagingVersion == "v1" {
			// v1: 每个模块独立, 使用模块名作为 key
			k = cfg.ModuleName
			imageTarExt = ".tgz"
		} else {
			// v2: 相同构建方案的模块共享
			k = fmt.Sprintf("%s%s", cfg.SourceDir, rBuildpacks)
			imageTarExt = ".tar"
		}

		if v, ok := groupMap[k]; !ok {
			groupMap[k] = &ModuleBuildGroup{
				SourceDir:          cfg.SourceDir,
				RequiredBuildpacks: rBuildpacks,
				Buildpacks:         cfg.Buildpacks,
				ModuleNames:        []string{cfg.ModuleName},
				BuildModuleName:    cfg.ModuleName,
				Envs:               cfg.Envs,
				OutputImage:        fmt.Sprintf("docker.io/local/%s:latest", cfg.ModuleName),
				OutputImageTarName: fmt.Sprintf("%s%s", cfg.ModuleName, imageTarExt),
			}
		} else {
			v.ModuleNames = append(v.ModuleNames, cfg.ModuleName)
			maps.Copy(v.Envs, cfg.Envs)
		}
	}

	return maps.Values(groupMap), nil
}

// ToRequiredBuildpacks 将 buildpacks 从 list 排序后, 转换成 string 结构.
// 格式如: oci-embedded bk-buildpack-apt ... v2;oci-embedded bk-buildpack-python ... v213
// NOTE: 在转换的过程中, 如果 buildpack 的 version 为空版本, 会采用默认版本替换
func ToRequiredBuildpacks(buildpacks []bcfg.Buildpack) (string, error) {
	slices.SortFunc(buildpacks, func(a, b bcfg.Buildpack) int {
		return strings.Compare(a.Name, b.Name)
	})

	var parts []string
	var err error

	for _, bp := range buildpacks {
		v := bp.Version
		if v == "" {
			v, err = bcfg.GetDefaultVersionByBPName(bp.Name)
			if err != nil {
				return "", err
			}
		}

		parts = append(parts, strings.Join([]string{config.G.BuildpackType, bp.Name, "...", v}, " "))

	}

	return strings.Join(parts, ";"), nil
}

// aptfileExists 检测 Aptfile 是否存在
func aptfileExists(moduleDir string) bool {
	if _, err := os.Stat(filepath.Join(moduleDir, "Aptfile")); err != nil {
		// 没有检测到有效的 Aptfile
		return false
	}
	return true
}

// detectLogoFile 探测当前应用源码是否有 logo 文件, 如果有, 则返回 logo 文件路径; 否则返回空字符串
func detectLogoFile(sourceDir string) string {
	for _, filename := range []string{"logo.png", "logo.jpg", "logo.jpeg"} {
		_, err := os.Stat(filepath.Join(sourceDir, filename))
		if err == nil {
			return filepath.Join(sourceDir, filename)
		}
	}
	// logo not found!
	return ""
}

// GenerateProcType 生成进程类型
func GenerateProcType(moduleName, procName string) string {
	return fmt.Sprintf("%s-%s", moduleName, procName)
}
