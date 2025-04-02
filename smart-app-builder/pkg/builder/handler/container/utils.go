package container

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/pkg/errors"
	"github.com/samber/lo"

	bcfg "github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/buildconfig"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/config"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/plan"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/utils"
)

// buildSourceTarball 生成 Procfile 文件后写入 sourceDir, 并将其打包成 destTGZ 文件
func buildSourceTarball(sourceDir, destTGZ string, Procfile map[string]string) error {
	procfileContent := ""
	for procName, procCommand := range Procfile {
		procfileContent += fmt.Sprintf("%s: %s\n", procName, procCommand)
	}

	procfilePath := filepath.Join(sourceDir, "Procfile")
	if err := os.WriteFile(procfilePath, []byte(procfileContent), 0o644); err != nil {
		return errors.Wrap(err, "failed to write Procfile")
	}

	if err := utils.ArchiveTGZ(sourceDir, destTGZ); err != nil {
		return errors.Wrap(err, "failed to archive")
	}

	return nil
}

// buildArtifactTarball 将 app_desc.yaml, logo, .Version 以及 artifact.json 写入 artifactDir,
// 并将 artifactDir 打包成 {app_code}.tgz 文件, 返回 {app_code}.tgz 的路径.
// 其中, artifact.json 描述应用模块与镜像 tar 的对应关系
func buildArtifactTarball(buildPlan *plan.BuildPlan, artifactDir string) (string, error) {
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
		return "", errors.Wrap(err, "failed to write builder flag .Version")
	}

	// 2. 生成 artifact.json, 写入 artifactDir
	if err := writeArtifactJsonFile(buildPlan, artifactDir); err != nil {
		return "", errors.Wrap(err, "failed to write artifact.json")
	}

	// 3. 打包成 {app_code}.tgz
	artifactTGZ := filepath.Join(artifactDir, fmt.Sprintf("%s.tgz", buildPlan.AppCode))
	if err := utils.ArchiveTGZ(artifactDir, artifactTGZ); err != nil {
		return "", errors.Wrap(err, "failed to archive")
	}
	return artifactTGZ, nil
}

// buildRunArgs 构建运行命令, 其中 moduleSrcTGZ 为模块源码包, runImage 为运行时镜像
func buildRunArgs(step *plan.ModuleBuildStep, moduleSrcTGZ string, runImage string) []string {
	args := make([]string, 0)

	envSlice := lo.MapToSlice(step.Envs, func(k string, v string) string {
		return fmt.Sprintf("%s=%s", k, v)
	})

	// 添加 buildpacks 环境变量
	lo.ForEach(step.Buildpacks, func(bp bcfg.Buildpack, index int) {
		envSlice = append(envSlice, bcfg.GetBuildpacksEnvs(bp.Name)...)
	})

	bindTarget := "/tmp/source.tgz"
	envSlice = append(
		envSlice,
		[]string{
			fmt.Sprintf("REQUIRED_BUILDPACKS=%s", step.RequiredBuildpacks),
			fmt.Sprintf("OUTPUT_IMAGE=%s", step.OutPutImage),
			fmt.Sprintf("CNB_RUN_IMAGE=%s", runImage),
			fmt.Sprintf("SOURCE_GET_URL=file://%s", bindTarget),
			"USE_DOCKER_DAEMON=true",
			"CNB_PLATFORM_API=0.11",
		}...)

	lo.ForEach(envSlice, func(env string, index int) {
		args = append(args, "-e", env)
	})

	// 挂载源码压缩包
	args = append(args, "--mount", fmt.Sprintf("type=bind,source=%s,target=%s", moduleSrcTGZ, bindTarget))

	args = append(
		args,
		"--mount",
		fmt.Sprintf("type=bind,source=%s,target=/var/run/docker.sock", config.G.DaemonSockFile),
	)

	return args
}

// writeArtifactJsonFile 根据 buildPlan, 在目录 artifactDir 写入 artifact.json.
// artifact.json 描述应用模块与镜像 tar 的对应关系, 格式如: {"module1": "module1.tar", "module2": "module2.tar"}
func writeArtifactJsonFile(buildPlan *plan.BuildPlan, artifactDir string) error {
	moduleArtifactRel := make(map[string]string)
	for _, step := range buildPlan.Steps {
		for _, module := range step.ModuleNames {
			moduleArtifactRel[module] = step.OutPutImageTarName
		}
	}
	relBytes, err := json.Marshal(moduleArtifactRel)
	if err != nil {
		return err
	}
	if err = os.WriteFile(filepath.Join(artifactDir, "artifact.json"), relBytes, 0o644); err != nil {
		return err
	}
	return nil
}
