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

// 组件管理器用于管理平台支持的各类组件及其不同版本
// 包括组件的模板定义、参数 Schema、文档等信息
//
// 目录结构说明：
//   components/
//   ├── cl5/                 # cl5 类型组件
//   │   ├── v1/              # v1版本
//   │   │   ├── template.yaml  # 组件部署模板
//   │   │   ├── schema.json    # 组件参数 Schema 定义
//   │   │   └── docs.md        # 组件详细文档说明
//   │   └── v2/              # v2版本
//   │       ├── template.yaml
//   │       ├── schema.json
//   │       └── docs.md
//   ├── env_overlay/              # env_overlay 类型组件
//   │   ├── v1/
//   │   │   ├── template.yaml
//   │   │   ├── schema.json
//   │   │   └── docs.md
//   │   └── v2/
//   │       ├── template.yaml
//   │       ├── schema.json
//   │       └── docs.md
//
// 主要功能：
//   - 组件信息的加载与管理
//   - 组件模板的获取
//   - 组件参数 Schema 的验证

package components

import (
	"encoding/json"
	"fmt"
	"github.com/pkg/errors"
	"os"
	"path/filepath"
	"strings"

	"github.com/xeipuuv/gojsonschema"
)

// DefaultComponentDir 默认存放组件的目录
var DefaultComponentDir = "/components"

// ComponentManager 管理所有组件
type ComponentManager struct {
	componentsDir string
}

// NewComponentManager 创建组件管理器
func NewComponentManager(componentsDir string) (*ComponentManager, error) {
	absPath, err := filepath.Abs(componentsDir)
	if err != nil {
		return nil, errors.Wrap(err, "get absolute path")
	}

	if _, err := os.Stat(absPath); os.IsNotExist(err) {
		return nil, errors.Wrap(err, "components directory does not exist")
	}

	return &ComponentManager{
		componentsDir: absPath,
	}, nil
}

// GetTemplate 获取组件模板内容
func (m *ComponentManager) GetTemplate(componentType, version string) ([]byte, error) {
	templatePath := filepath.Join(m.componentsDir, componentType, version, "template.yaml")
	return m.readFileContent(templatePath)
}

// GetSchema 获取组件 schema 内容
func (m *ComponentManager) GetSchema(componentType, version string) ([]byte, error) {
	schemaPath := filepath.Join(m.componentsDir, componentType, version, "schema.json")
	return m.readFileContent(schemaPath)
}

// GetComponentInfo 获取组件的完整信息
func (m *ComponentManager) GetComponentInfo(componentType, version string) (*ComponentInfo, error) {
	template, err := m.GetTemplate(componentType, version)
	if err != nil {
		return nil, err
	}

	schema, err := m.GetSchema(componentType, version)
	if err != nil {
		return nil, err
	}

	return &ComponentInfo{
		Type:     componentType,
		Version:  version,
		Template: template,
		Schema:   schema,
	}, nil
}

// ValidateSchema 验证给定的参数是否符合组件的 schema
func (m *ComponentManager) ValidateSchema(componentType, version string, properties map[string]any) error {
	schema, err := m.GetSchema(componentType, version)
	if err != nil {
		return err
	}

	var schemaObj interface{}
	if err := json.Unmarshal(schema, &schemaObj); err != nil {
		return errors.Wrap(err, "invalid component schema JSON")
	}
	schemaLoader := gojsonschema.NewGoLoader(schemaObj)
	paramsLoader := gojsonschema.NewGoLoader(properties)
	result, err := gojsonschema.Validate(schemaLoader, paramsLoader)
	if err != nil {
		return errors.Wrap(err, "schema validation")
	}

	if !result.Valid() {
		var errMsgs []string
		for _, desc := range result.Errors() {
			errMsgs = append(errMsgs, fmt.Sprintf("- %s", desc))
		}
		msg := fmt.Sprintf("component  validation failed: %s", strings.Join(errMsgs, "\n"))
		return errors.New(msg)
	}

	return nil
}

// readFileContent 读取文件内容
func (m *ComponentManager) readFileContent(filePath string) ([]byte, error) {
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		return nil, errors.Wrap(err, "read component file")
	}

	content, err := os.ReadFile(filePath)
	if err != nil {
		return nil, errors.Wrap(err, "read component file")
	}

	return content, nil
}
