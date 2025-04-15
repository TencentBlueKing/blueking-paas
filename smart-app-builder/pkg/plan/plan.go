package plan

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"slices"

	"github.com/pkg/errors"
	"golang.org/x/exp/maps"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/appdesc"
	bcfg "github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/buildconfig"
)

const AppDescFileName = "app_desc.yaml"

// BuildPlan 定义了应用的构建方案，包含所有模块的构建配置分组。
// 采用相同构建方案的模块会合并到同一构建组，复用同一份构建制品。
// 相同构建方案判定标准：
//   - 代码目录相同
//   - 构建语言或 buildpacks 相同
type BuildPlan struct {
	// AppCode 应用 code
	AppCode string
	// AppDescPath 应用描述文件路径
	AppDescPath string
	// LogoFilePath 应用 Logo 文件路径
	LogoFilePath string
	// Procfile 进程与启动命令的映射
	Procfile map[string]string
	// BuildGroups 模块构建组列表
	BuildGroups []*ModuleBuildGroup
}

// ModuleBuildGroup 是共享相同构建配置的模块分组，组内所有模块复用同一个构建流程(仅构建一次)和输出镜像
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

	procfile := desc.GenerateProcfile()
	if len(procfile) == 0 {
		return nil, errors.New("no valid processes found in app_desc.yaml")
	}

	groups, err := buildModuleBuildGroups(sourceDir, desc)
	if err != nil {
		return nil, err
	}

	plan := &BuildPlan{
		AppCode:      desc.GetAppCode(),
		AppDescPath:  filepath.Join(sourceDir, AppDescFileName),
		LogoFilePath: detectLogoFile(sourceDir),
		Procfile:     procfile,
		BuildGroups:  groups,
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

		// 合并采用相同构建方案的模块
		k := fmt.Sprintf("%s%s", cfg.SourceDir, rBuildpacks)
		if v, ok := groupMap[k]; !ok {
			groupMap[k] = &ModuleBuildGroup{
				SourceDir:          cfg.SourceDir,
				RequiredBuildpacks: rBuildpacks,
				Buildpacks:         cfg.Buildpacks,
				ModuleNames:        []string{cfg.ModuleName},
				BuildModuleName:    cfg.ModuleName,
				Envs:               cfg.Envs,
				OutputImage:        fmt.Sprintf("docker.io/local/%s:latest", cfg.ModuleName),
				OutputImageTarName: fmt.Sprintf("%s.tar", cfg.ModuleName),
			}
		} else {
			v.ModuleNames = append(v.ModuleNames, cfg.ModuleName)
			maps.Copy(v.Envs, cfg.Envs)
		}
	}

	return maps.Values(groupMap), nil
}

// ToRequiredBuildpacks 将 buildpacks 从 list 排序后, 转换成 string 结构.
// 格式如: tgz bk-buildpack-apt ... v2;tgz bk-buildpack-python ... v213
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
