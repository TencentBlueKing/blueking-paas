package plan

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/pkg/errors"
	"golang.org/x/exp/maps"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/appdesc"
	bcfg "github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/buildconfig"
)

const AppDescFileName = "app_desc.yaml"

// BuildPlan 构建计划
type BuildPlan struct {
	AppCode      string
	AppDescPath  string
	LogoFilePath string
	Procfile     map[string]string
	Steps        []*ModuleBuildStep
}

// ModuleBuildStep 模块构建步骤配置
type ModuleBuildStep struct {
	// SourceDir 是 app_desc.yaml 中模块的代码路径(相对路径)
	SourceDir string
	// RequiredBuildpacks 格式如: tgz bk-buildpack-apt ... v2;tgz bk-buildpack-python ... v213
	RequiredBuildpacks string
	Buildpacks         []bcfg.Buildpack
	// BuildModuleName 是当前步骤在构建镜像时, 实际的目标模块
	BuildModuleName string
	// ModuleNames 记录了最终共用 OutPutImage 的模块, 其中也包括 BuildModuleName
	ModuleNames []string
	// Envs 是当前步骤所需要的环境变量
	Envs map[string]string
	// OutPutImage 是当前步骤构建出的镜像
	OutPutImage string
	// OutPutImageTarName 是当前步骤构建出的镜像的压缩包名
	OutPutImageTarName string
}

// PrepareBuildPlan 解析 app_desc.yaml 文件, 生成 BuildPlan
func PrepareBuildPlan(sourceDir string) (*BuildPlan, error) {
	if err := ensureAppDescYaml(sourceDir); err != nil {
		return nil, err
	}

	desc, err := appdesc.ParseAppDescYAML(filepath.Join(sourceDir, AppDescFileName))
	if err != nil {
		return nil, errors.Wrap(err, "parse app_desc.yaml error")
	}

	if err = desc.Validate(); err != nil {
		return nil, err
	}

	procfile := desc.GenerateProcfile()
	if len(procfile) == 0 {
		return nil, errors.New("no valid processes found in app_desc.yaml")
	}

	steps, err := buildSteps(sourceDir, desc)
	if err != nil {
		return nil, err
	}

	plan := &BuildPlan{
		AppCode:      desc.GetAppCode(),
		AppDescPath:  filepath.Join(sourceDir, AppDescFileName),
		LogoFilePath: detectLogoFile(sourceDir),
		Procfile:     procfile,
		Steps:        steps,
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

// buildSteps 生成构建步骤
func buildSteps(sourceDir string, desc appdesc.AppDesc) ([]*ModuleBuildStep, error) {
	configs, err := desc.GenerateModuleBuildConfig()
	if err != nil {
		return nil, err
	}

	stepMap := make(map[string]*ModuleBuildStep)

	for _, cfg := range configs {
		if aptfileExists(filepath.Join(sourceDir, cfg.SourceDir)) {
			bp, _ := bcfg.GetBuildpackByLanguage("apt")
			cfg.Buildpacks = append(cfg.Buildpacks, *bp)
		}

		rBuildpacks, err := ToRequiredBuildpacks(cfg.Buildpacks)
		if err != nil {
			return nil, err
		}

		// 合并采用相同构建方案的模块
		k := fmt.Sprintf("%s%s", cfg.SourceDir, rBuildpacks)
		if v, ok := stepMap[k]; !ok {
			stepMap[k] = &ModuleBuildStep{
				SourceDir:          cfg.SourceDir,
				RequiredBuildpacks: rBuildpacks,
				Buildpacks:         cfg.Buildpacks,
				ModuleNames:        []string{cfg.ModuleName},
				BuildModuleName:    cfg.ModuleName,
				Envs:               cfg.Envs,
				OutPutImage:        fmt.Sprintf("docker.io/local/%s:latest", cfg.ModuleName),
				OutPutImageTarName: fmt.Sprintf("%s.tar", cfg.ModuleName),
			}
		} else {
			v.ModuleNames = append(v.ModuleNames, cfg.ModuleName)
			maps.Copy(v.Envs, cfg.Envs)
		}
	}

	return maps.Values(stepMap), nil
}

// ToRequiredBuildpacks 将 buildpacks 从 list 排序后, 转换成 string 结构.
// 格式如: tgz bk-buildpack-apt ... v2;tgz bk-buildpack-python ... v213
// NOTE: 在转换的过程中, 如果 buildpack 的 version 为空版本, 会采用默认版本替换
func ToRequiredBuildpacks(buildpacks []bcfg.Buildpack) (string, error) {
	sort.Slice(buildpacks, func(i, j int) bool {
		return strings.Compare(buildpacks[i].Name, buildpacks[j].Name) > 0
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

		parts = append(parts, strings.Join([]string{"tgz", bp.Name, "...", v}, " "))

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
