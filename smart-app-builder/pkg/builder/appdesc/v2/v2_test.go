package v2_test

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"gopkg.in/yaml.v3"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/appdesc/v2"
	bcfg "github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/buildconfig"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/config"
)

var _ = Describe("V2", func() {
	// 设置全局配置
	config.SetGlobalConfig()

	Describe("normal", func() {
		var appDescConfig v2.AppDescConfig

		BeforeEach(func() {
			content := []byte(`spec_version: 2
app_version: 1.0.0
app:
  bk_app_code: test-app-code
modules:
  api:
    language: go
    source_dir: backend
    processes:
      api-process:
        command: go run main.go
    env_variables:
      - key: key1
        value: value1
  web:
    language: python
    source_dir: frontend
    processes:
      web-process:
        command: python main.py`)

			Expect(yaml.Unmarshal(content, &appDescConfig)).To(BeNil())
			Expect(appDescConfig.Validate()).To(BeNil())
		})

		It("get app code", func() {
			Expect(appDescConfig.GetAppCode()).To(Equal("test-app-code"))
		})
		It("get module build config", func() {
			buildConfig, _ := appDescConfig.GenerateModuleBuildConfig()

			expectedPythonConfig := bcfg.ModuleBuildConfig{
				SourceDir:  "frontend",
				ModuleName: "web",
				Buildpacks: []bcfg.Buildpack{
					{Name: "bk-buildpack-python", Version: "v213"},
				},
				Envs: map[string]string{},
			}
			expectedGoConfig := bcfg.ModuleBuildConfig{
				SourceDir:  "backend",
				ModuleName: "api",
				Envs: map[string]string{
					"key1": "value1",
				},
				Buildpacks: []bcfg.Buildpack{{Name: "bk-buildpack-go", Version: "v191"}},
			}

			if buildConfig[0].ModuleName == "api" {
				Expect(buildConfig[0]).To(Equal(expectedGoConfig))
				Expect(buildConfig[1]).To(Equal(expectedPythonConfig))
			} else {
				Expect(buildConfig[0]).To(Equal(expectedPythonConfig))
				Expect(buildConfig[1]).To(Equal(expectedGoConfig))
			}
		})
		It("get procfile", func() {
			procfile := appDescConfig.GenerateProcfile()
			Expect(procfile["web-web-process"]).To(Equal("python main.py"))
			Expect(procfile["api-api-process"]).To(Equal("go run main.go"))
		})
	})

	Describe("invalid", func() {
		var appDescConfig v2.AppDescConfig

		It("missing app code", func() {
			content := []byte(`spec_version: 2
app_version: 1.0`)

			Expect(yaml.Unmarshal(content, &appDescConfig)).To(BeNil())
			Expect(appDescConfig.Validate().Error()).To(Equal("app code is empty"))
		})

		It("missing modules", func() {
			content := []byte(`spec_version: 2
app_version: 1.0
app:
  bk_app_code: test-app-code`)
			Expect(yaml.Unmarshal(content, &appDescConfig)).To(BeNil())
			Expect(appDescConfig.Validate().Error()).To(Equal("modules is empty"))
		})
		It("missing processes", func() {
			content := []byte(`spec_version: 2
app_version: 1.0
app:
  bk_app_code: test-app-code
modules:
  api:
    language: go`)
			Expect(yaml.Unmarshal(content, &appDescConfig)).To(BeNil())
			Expect(appDescConfig.Validate().Error()).To(Equal("processes of module api is empty"))
		})

		It("invalid app version", func() {
			content := []byte(`spec_version: 2
app_version: 1.0.0.0
app:
  bk_app_code: test-app-code
modules:
  api:
    language: go
    source_dir: backend
    processes:
      api-process:
        command: go run main.go`)
			Expect(yaml.Unmarshal(content, &appDescConfig)).To(BeNil())
			Expect(appDescConfig.Validate()).NotTo(BeNil())
		})
	})
})
