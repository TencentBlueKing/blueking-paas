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
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/pkg/errors"
	"github.com/xeipuuv/gojsonschema"
)

// DefaultComponentDir 默认存放组件的目录
var DefaultComponentDir = "/components"

// ComponentLoader 读取所有组件
type ComponentLoader struct {
	componentsDir string
}

// NewComponentLoader 创建组件加载器
func NewComponentLoader() (*ComponentLoader, error) {
	absPath, err := filepath.Abs(DefaultComponentDir)
	if err != nil {
		return nil, errors.Wrap(err, "get absolute path")
	}

	if _, err := os.Stat(absPath); os.IsNotExist(err) {
		return nil, errors.Wrap(err, "components directory does not exist")
	}

	return &ComponentLoader{
		componentsDir: absPath,
	}, nil
}

// GetTemplate 获取组件模板内容
func (m *ComponentLoader) GetTemplate(componentName, version string) ([]byte, error) {
	templatePath := filepath.Join(m.componentsDir, componentName, version, "template.yaml")
	return m.readFileContent(templatePath)
}

// GetSchema 获取组件 schema 内容
func (m *ComponentLoader) GetSchema(componentName, version string) ([]byte, error) {
	schemaPath := filepath.Join(m.componentsDir, componentName, version, "schema.json")
	return m.readFileContent(schemaPath)
}

// GetComponentInfo 获取组件的完整信息
func (m *ComponentLoader) GetComponentInfo(componentName, version string) (*ComponentInfo, error) {
	template, err := m.GetTemplate(componentName, version)
	if err != nil {
		return nil, err
	}

	schema, err := m.GetSchema(componentName, version)
	if err != nil {
		return nil, err
	}

	return &ComponentInfo{
		Name:     componentName,
		Version:  version,
		Template: template,
		Schema:   schema,
	}, nil
}

// ValidateSchema 验证给定的参数是否符合组件的 schema
func (m *ComponentLoader) ValidateSchema(componentName, version string, properties map[string]any) error {
	schema, err := m.GetSchema(componentName, version)
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
		msg := fmt.Sprintf("properties validation failed: %s", strings.Join(errMsgs, "\n"))
		return errors.New(msg)
	}

	return nil
}

// readFileContent 读取文件内容
func (m *ComponentLoader) readFileContent(filePath string) ([]byte, error) {
	content, err := os.ReadFile(filePath)
	if err != nil {
		return nil, errors.Wrap(err, "read component file")
	}

	return content, nil
}
