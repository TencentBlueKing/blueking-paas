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

package appdesc_test

import (
	"os"
	"path/filepath"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/appdesc"
)

var _ = Describe("ParseAppDescYAML", func() {
	var yamlDir string
	var yamlPath string

	BeforeEach(func() {
		yamlDir, _ = os.MkdirTemp("", "tmp")
		yamlPath = filepath.Join(yamlDir, "app_desc.yaml")
	})
	AfterEach(func() {
		Expect(os.RemoveAll(yamlDir)).To(BeNil())
	})

	It("parse app desc v2", func() {
		content := []byte(`spec_version: 2
app_version: 1.0.0
app:
  bk_app_code: test-app-code
modules:
  default:
    language: python
    processes:
      web:
        command: python main.py
  backend:
    language: go
    processes:
      api-process:
        command: go run main.go`)

		Expect(os.WriteFile(yamlPath, content, 0o644)).To(BeNil())
		appDesc, err := appdesc.ParseAppDescYAML(yamlPath)
		Expect(err).To(BeNil())
		Expect(appDesc.GetAppCode()).To(Equal("test-app-code"))

		procCommands := appDesc.GenerateProcessCommands()
		Expect(procCommands["default"]["web"]).To(Equal("python main.py"))
		Expect(procCommands["backend"]["api-process"]).To(Equal("go run main.go"))
	})

	It("parse app desc v3", func() {
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
  - name: api
    language: go
    sourceDir: backend
    spec:
      processes:
        - name: api-process
          procCommand: go run main.go`)

		Expect(os.WriteFile(yamlPath, content, 0o644)).To(BeNil())
		appDesc, err := appdesc.ParseAppDescYAML(yamlPath)
		Expect(err).To(BeNil())
		Expect(appDesc.GetAppCode()).To(Equal("test-app-code"))

		procCommands := appDesc.GenerateProcessCommands()
		Expect(procCommands["api"]["api-process"]).To(Equal("go run main.go"))
		Expect(procCommands["web"]["web-process"]).To(Equal("python main.py"))
	})

	It("parse invalid spec version", func() {
		content := []byte(`spec_version: 1
app_version: 1.0.0`)

		Expect(os.WriteFile(yamlPath, content, 0o644)).To(BeNil())
		_, err := appdesc.ParseAppDescYAML(yamlPath)
		Expect(err).NotTo(BeNil())
	})
})
