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

package v2_test

import (
	"slices"
	"strings"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"gopkg.in/yaml.v3"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/appdesc/v2"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/buildconfig"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/config"
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

			expectedPythonConfig := buildconfig.ModuleBuildConfig{
				SourceDir:  "frontend",
				ModuleName: "web",
				Buildpacks: []buildconfig.Buildpack{
					{Name: "bk-buildpack-python", Version: "v213"},
				},
				Envs: map[string]string{},
			}
			expectedGoConfig := buildconfig.ModuleBuildConfig{
				SourceDir:  "backend",
				ModuleName: "api",
				Envs: map[string]string{
					"key1": "value1",
				},
				Buildpacks: []buildconfig.Buildpack{{Name: "bk-buildpack-go", Version: "v205"}},
			}

			slices.SortFunc(buildConfig, func(a, b buildconfig.ModuleBuildConfig) int {
				return strings.Compare(a.ModuleName, b.ModuleName)
			})

			Expect(buildConfig[0]).To(Equal(expectedGoConfig))
			Expect(buildConfig[1]).To(Equal(expectedPythonConfig))
		})
		It("GenerateProcessCommands", func() {
			procCommands := appDescConfig.GenerateProcessCommands()
			Expect(procCommands["web"]["web-process"]).To(Equal("python main.py"))
			Expect(procCommands["api"]["api-process"]).To(Equal("go run main.go"))
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
