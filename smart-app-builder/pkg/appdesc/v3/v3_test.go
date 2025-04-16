package v3_test

import (
	"slices"
	"strings"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"gopkg.in/yaml.v3"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/appdesc/v3"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/buildconfig"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/config"
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

			expectedPythonConfig := buildconfig.ModuleBuildConfig{
				SourceDir:  ".",
				ModuleName: "web",
				Envs:       map[string]string{"key1": "value1"},
				Buildpacks: []buildconfig.Buildpack{
					{Name: "bk-buildpack-python", Version: "test-version"},
				},
			}
			expectedGoConfig := buildconfig.ModuleBuildConfig{
				SourceDir:  "backend",
				ModuleName: "api",
				Envs:       map[string]string{},
				Buildpacks: []buildconfig.Buildpack{{Name: "bk-buildpack-go", Version: "v205"}},
			}

			slices.SortFunc(buildConfig, func(a, b buildconfig.ModuleBuildConfig) int {
				return strings.Compare(a.ModuleName, b.ModuleName)
			})

			Expect(buildConfig[0]).To(Equal(expectedGoConfig))
			Expect(buildConfig[1]).To(Equal(expectedPythonConfig))
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
