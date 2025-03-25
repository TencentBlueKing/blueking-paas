package buildconfig

import (
	"fmt"
	"strings"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/config"
)

// Buildpack 构建工具
type Buildpack struct {
	Name    string `yaml:"name"`
	Version string `yaml:"version,omitempty"`
}

// GetBuildpackByLanguage 根据语言获取对应的 buildpack
func GetBuildpackByLanguage(language string) (*Buildpack, error) {
	if bp, ok := getDefaultBuildpacks()[strings.ToLower(language)]; ok {
		return &bp, nil
	}
	return nil, fmt.Errorf("no buildpacks match with language: %s", language)
}

// GetDefaultVersionByBPName 根据 buildpack 的名字, 获取它的默认版本
func GetDefaultVersionByBPName(name string) (string, error) {
	// python 的 buildpack 配置 https://github.com/TencentBlueKing/blueking-paas/blob/builder-stack/cloudnative-buildpacks/buildpacks/bk-buildpack-python/cnb-buildpack/buildpack.toml
	for _, v := range getDefaultBuildpacks() {
		if v.Name == name {
			return v.Version, nil
		}
	}
	return "", fmt.Errorf("no buildpacks match with name: %s", name)
}

// GetBuildpacksEnvs return buildpacks 的环境变量
func GetBuildpacksEnvs(name string) []string {
	var envs []string
	bpEnvs := make([]string, 0)

	switch name {
	case "bk-buildpack-python":
		for _, key := range []string{
			"PIP_VERSION", "DISABLE_COLLECTSTATIC", "BUILDPACK_S3_BASE_URL", "PIP_INDEX_URL",
			"PIP_EXTRA_INDEX_URL",
		} {
			bpEnvs = append(bpEnvs, fmt.Sprintf("%s=%s", key, config.G.GetString(key)))
		}
	case "bk-buildpack-nodejs":
		for _, key := range []string{"STDLIB_FILE_URL", "S3_DOMAIN", "NPM_REGISTRY"} {
			bpEnvs = append(bpEnvs, fmt.Sprintf("%s=%s", key, config.G.GetString(key)))
		}
	case "bk-buildpack-go":
		bpEnvs = append(bpEnvs, fmt.Sprintf("GO_BUCKET_URL=%s", config.G.GetString("GO_BUCKET_URL")))
	}

	return append(envs, bpEnvs...)
}

func getDefaultBuildpacks() map[string]Buildpack {
	return map[string]Buildpack{
		"python": {Name: "bk-buildpack-python", Version: config.G.GetString("PYTHON_BUILDPACK_VERSION")},
		"nodejs": {Name: "bk-buildpack-nodejs", Version: config.G.GetString("NODEJS_BUILDPACK_VERSION")},
		"go":     {Name: "bk-buildpack-go", Version: config.G.GetString("GO_BUILDPACK_VERSION")},
		"apt":    {Name: "bk-buildpack-apt", Version: config.G.GetString("APT_BUILDPACK_VERSION")},
	}
}
