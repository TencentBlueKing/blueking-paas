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

package components

import (
	"os"
	"path/filepath"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("ComponentLoader", func() {
	var manager *ComponentLoader
	var tempDir string

	const (
		validComponentName   = "web"
		validVersion         = "v1"
		invalidComponentName = "invalid"
		invalidVersion       = "v999"
	)

	BeforeEach(func() {
		var err error
		tempDir, err = os.MkdirTemp("", "components_test")
		DefaultComponentDir = tempDir
		Expect(err).NotTo(HaveOccurred())

		// 创建测试组件结构
		createTestComponent(tempDir, validComponentName, validVersion, `{"key": "value"}`, "template: content")
		env_overlay_schema := `{
  "type": "object",
  "required": ["env"],
  "properties": {
    "env": {
      "type": "object",
      "additionalProperties": {
        "type": "string"
      }
    }
  }
}`
		createTestComponent(tempDir, "env_overlay", "v1", env_overlay_schema, "template: overlay")

		manager, err = NewComponentLoader()
		Expect(err).NotTo(HaveOccurred())
	})

	AfterEach(func() {
		Expect(os.RemoveAll(tempDir)).To(Succeed())
	})

	Describe("NewComponentLoader", func() {
		Context("when directory exists", func() {
			It("should create manager successfully", func() {
				_, err := NewComponentLoader()
				Expect(err).NotTo(HaveOccurred())
			})
		})
	})

	Describe("GetTemplate", func() {
		Context("with valid component and version", func() {
			It("should return template content", func() {
				content, err := manager.GetTemplate(validComponentName, validVersion)
				Expect(err).NotTo(HaveOccurred())
				Expect(string(content)).To(Equal("template: content"))
			})
		})

		Context("with invalid component", func() {
			It("should return error", func() {
				_, err := manager.GetTemplate(invalidComponentName, validVersion)
				Expect(err).To(HaveOccurred())
			})
		})

		Context("with invalid version", func() {
			It("should return error", func() {
				_, err := manager.GetTemplate(validComponentName, invalidVersion)
				Expect(err).To(HaveOccurred())
			})
		})
	})

	Describe("GetSchema", func() {
		Context("with valid component and version", func() {
			It("should return schema content", func() {
				content, err := manager.GetSchema(validComponentName, validVersion)
				Expect(err).NotTo(HaveOccurred())
				Expect(string(content)).To(Equal(`{"key": "value"}`))
			})
		})

		Context("with invalid schema file", func() {
			It("should return error", func() {
				_, err := manager.GetSchema("invalid", "v1")
				Expect(err).To(HaveOccurred())
			})
		})
	})

	Describe("ValidateSchema", func() {
		Context("with valid params", func() {
			It("should return nil", func() {
				params := map[string]any{
					"env": map[string]string{
						"KEY": "value",
					},
				}
				err := manager.ValidateSchema("env_overlay", "v1", params)
				Expect(err).NotTo(HaveOccurred())
			})
		})

		Context("with invalid params", func() {
			It("should return validation errors", func() {
				params := map[string]any{
					"env": "not_an_object",
				}
				err := manager.ValidateSchema("env_overlay", "v1", params)
				Expect(err).To(HaveOccurred())
				Expect(err.Error()).To(ContainSubstring("validation failed"))
			})
		})
	})

	Describe("GetComponentInfo", func() {
		Context("with valid component and version", func() {
			It("should return complete component info", func() {
				info, err := manager.GetComponentInfo(validComponentName, validVersion)
				Expect(err).NotTo(HaveOccurred())
				Expect(info.Name).To(Equal(validComponentName))
				Expect(info.Version).To(Equal(validVersion))
				Expect(string(info.Template)).To(Equal("template: content"))
				Expect(string(info.Schema)).To(Equal(`{"key": "value"}`))
			})
		})

		Context("with invalid component", func() {
			It("should return error", func() {
				_, err := manager.GetComponentInfo(invalidComponentName, validVersion)
				Expect(err).To(HaveOccurred())
			})
		})
	})
})

func createTestComponent(baseDir, cName, version, schema, template string) {
	versionDir := filepath.Join(baseDir, cName, version)
	Expect(os.MkdirAll(versionDir, 0o755)).To(Succeed())

	// 创建 schema.json
	schemaPath := filepath.Join(versionDir, "schema.json")
	Expect(os.WriteFile(schemaPath, []byte(schema), 0o644)).To(Succeed())

	// 创建 template.yaml
	templatePath := filepath.Join(versionDir, "template.yaml")
	Expect(os.WriteFile(templatePath, []byte(template), 0o644)).To(Succeed())
}
