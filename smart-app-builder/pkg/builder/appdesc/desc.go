package appdesc

import (
	"os"

	"gopkg.in/yaml.v3"
	"github.com/pkg/errors"

	descv2 "github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/appdesc/v2"
	descv3 "github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/appdesc/v3"
	bcfg "github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/buildconfig"
)

// AppDesc app_desc
type AppDesc interface {
	// GetAppCode 获取 app_code
	GetAppCode() string
	// Validate 验证 app_desc
	Validate() error
	// GenerateProcfile 生成 Procfile
	GenerateProcfile() map[string]string
	// GenerateModuleBuildConfig 生成 ModuleBuildConfig
	GenerateModuleBuildConfig() ([]bcfg.ModuleBuildConfig, error)
}

// ParseAppDescYAML 解析 app_desc.yaml, 返回 AppDesc
func ParseAppDescYAML(yamlPath string) (AppDesc, error) {
	yamlContent, err := os.ReadFile(yamlPath)
	if err != nil {
		return nil, err
	}

	var configV2 descv2.AppDescConfig
	err = yaml.Unmarshal(yamlContent, &configV2)
	if err == nil && configV2.SpecVersion == 2 {
		return &configV2, nil
	}

	var configV3 descv3.AppDescConfig
	if err = yaml.Unmarshal(yamlContent, &configV3); err != nil {
		return nil, err
	}
	if configV3.SpecVersion == 3 {
		return &configV3, nil
	}

	return nil, errors.New("spec version must be 2 or 3")
}
