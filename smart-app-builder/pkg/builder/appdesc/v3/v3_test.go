package v3_test

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"gopkg.in/yaml.v3"

	v3 "github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/appdesc/v3"
	bcfg "github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/buildconfig"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/config"
)

var _ = Describe("V3", func() {
	// 设置全局配置
	config.SetGlobalConfig()

	Describe("normal", func() {
		var appDescConfig v3.AppDescConfig

		BeforeEach(func() {
			content := []byte(`specVersion: 3
appVersion: 1.0.0
app:
  bkAppCode: test-app-code
modules:
  - name: web
    language: python
    spec:
      processes:
        - name: web-process
          procCommand: python main.py
      configuration:
          env:
            - name: key1
              value: value1
      build:
         buildpacks:
          - name: bk-buildpack-python
            version: test-version
  - name: api
    language: go
    sourceDir: backend
    spec:
      processes:
        - name: api-process
          procCommand: go run main.go
        - name: beat
          procCommand: go run beat.go`)

			Expect(yaml.Unmarshal(content, &appDescConfig)).To(BeNil())
			Expect(appDescConfig.Validate()).To(BeNil())
		})

		It("get app code", func() {
			Expect(appDescConfig.GetAppCode()).To(Equal("test-app-code"))
		})

		It("get module build config", func() {
			buildConfig, _ := appDescConfig.GenerateModuleBuildConfig()

			expectedPythonConfig := bcfg.ModuleBuildConfig{
				SourceDir:  ".",
				ModuleName: "web",
				Envs:       map[string]string{"key1": "value1"},
				Buildpacks: []bcfg.Buildpack{
					{Name: "bk-buildpack-python", Version: "test-version"},
				},
			}
			expectedGoConfig := bcfg.ModuleBuildConfig{
				SourceDir:  "backend",
				ModuleName: "api",
				Envs:       map[string]string{},
				Buildpacks: []bcfg.Buildpack{{Name: "bk-buildpack-go", Version: "v191"}},
			}
			if buildConfig[0].ModuleName == "web" {
				Expect(buildConfig[0]).To(Equal(expectedPythonConfig))
				Expect(buildConfig[1]).To(Equal(expectedGoConfig))
			} else {
				Expect(buildConfig[0]).To(Equal(expectedGoConfig))
				Expect(buildConfig[1]).To(Equal(expectedPythonConfig))
			}
		})
	})
	Describe("invalid", func() {
		var appDescConfig v3.AppDescConfig
		It("missing app code", func() {
			content := []byte(`specVersion: 3
appVersion: 1.0.0
`)
			Expect(yaml.Unmarshal(content, &appDescConfig)).To(BeNil())
			Expect(appDescConfig.Validate().Error()).To(Equal("app code is empty"))
		})

		It("missing modules", func() {
			content := []byte(`specVersion: 3
appVersion: 1.0.0
app:
  bkAppCode: test-app-code`)
			Expect(yaml.Unmarshal(content, &appDescConfig)).To(BeNil())
			Expect(appDescConfig.Validate().Error()).To(Equal("modules is empty"))
		})

		It("missing processes", func() {
			content := []byte(`specVersion: 3
appVersion: 1.0.0
app:
  bkAppCode: test-app-code
modules:
  - name: web
    language: python
    spec:
      configuration:
          env:
            - name: key1
              value: value1`)
			Expect(yaml.Unmarshal(content, &appDescConfig)).To(BeNil())
			Expect(appDescConfig.Validate().Error()).To(Equal("processes of module web is empty"))
		})
	})
})
