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

package appdesc

import (
	"fmt"
	"os"
	"strings"

	"github.com/pkg/errors"
	"gopkg.in/yaml.v3"
)

// AppDescVersion 描述文件版本
type AppDescVersion string

const (
	appSpecVersion2 AppDescVersion = "2"
	appSpecVersion3 AppDescVersion = "3"
)

// Process ...
type Process struct {
	Name        string
	ProcCommand string
}

// Env ...
type Env struct {
	Name  string
	Value string
}

// AppSpecVersionLegacy ...
type AppSpecVersionLegacy struct {
	SpecVersion string `yaml:"spec_version"`
}

// AppSpecVersion ...
type AppSpecVersion struct {
	SpecVersion string `yaml:"specVersion"`
}

// GetAppSpecVersion ...
func GetAppSpecVersion(data []byte) (AppDescVersion, error) {
	// 尝试通过 AppSpecVersionLegacy 解析
	//var specLegacy AppSpecVersionLegacy
	specLegacy := new(AppSpecVersionLegacy)
	if err := yaml.Unmarshal(data, &specLegacy); err != nil {
		return "", err
	}

	switch specLegacy.SpecVersion {
	case "2":
		return appSpecVersion2, nil
	case "":
		// skip
	default:
		return "", fmt.Errorf("invalid legacy spec version: %s", specLegacy.SpecVersion)
	}

	// 通过 AppSpecVersion 解析
	var specVersion AppSpecVersion
	if err := yaml.Unmarshal(data, &specVersion); err != nil {
		return "", err
	}

	switch specVersion.SpecVersion {
	case "3":
		return appSpecVersion3, nil
	default:
		return "", fmt.Errorf("invalid spec version: %s", specVersion.SpecVersion)
	}

}

// CreateAppSpec creates a new AppDesc instance based on the given AppDescVersion
func CreateAppSpec(appSpecVersion AppDescVersion) (AppDesc, error) {
	switch appSpecVersion {
	case appSpecVersion2:
		return new(AppDescV2), nil
	case appSpecVersion3:
		return new(AppDescV3), nil
	default:
		return nil, errors.New("invalid app spec version")
	}
}

// UnmarshalToAppDesc reads from the given app_desc.yaml and unmarshals it into an AppDesc struct.
// Compatible with v2 and v3 versions of app_desc.yaml
func UnmarshalToAppDesc(descFilePath string) (AppDesc, error) {
	yamlFile, err := os.ReadFile(descFilePath)
	if err != nil {
		return nil, errors.Wrap(err, "failed to read app desc file")
	}
	appSpecVersion, err := GetAppSpecVersion(yamlFile)
	if err != nil {
		return nil, errors.Wrap(err, "failed to unmarshal app spec versions")
	}
	desc, err := CreateAppSpec(appSpecVersion)
	if err != nil {
		return nil, err
	}

	if err = yaml.Unmarshal(yamlFile, desc); err != nil {
		return nil, errors.Wrap(err, "failed to unmarshal app desc")
	}
	return desc, nil
}

// TransformToProcfile transforms an app_desc.yaml file into a Procfile string.
//
// It takes a path to an app_desc.yaml file as input and returns a string
// representation of a Procfile.
func TransformToProcfile(descFilePath string) (string, error) {
	desc, err := UnmarshalToAppDesc(descFilePath)
	if err != nil {
		return "", err
	}

	lines := []string{}
	for _, p := range desc.GetProcesses() {
		lines = append(lines, fmt.Sprintf("%s: %s", p.Name, p.ProcCommand))
	}

	return strings.Join(lines, "\n"), nil
}
