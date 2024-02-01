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

	"gopkg.in/yaml.v3"
)

// Process ...
type Process struct {
	Command string `yaml:"command"`
}

// AppDesc ...
type AppDesc struct {
	SpecVersion string `yaml:"spec_version"`
	Module      struct {
		Processes map[string]Process `yaml:"processes"`
		Scripts   struct {
			PreReleaseHook string `yaml:"pre_release_hook"`
		} `yaml:"scripts"`
	} `yaml:"module"`
}

// ParsePreReleaseHook parses the pre-release hook from the given app_desc.yaml.
//
// It takes a `descFilePath` parameter which is the path to the app_desc.yaml.
// It returns a string which represents the pre-release hook and an error if any occurred.
func ParsePreReleaseHook(descFilePath string) (string, error) {
	yamlFile, err := os.ReadFile(descFilePath)
	if err != nil {
		return "", err
	}

	desc := AppDesc{}
	if err = yaml.Unmarshal(yamlFile, &desc); err != nil {
		return "", err
	}

	return desc.Module.Scripts.PreReleaseHook, nil
}

// TransformToProcfile transforms an app_desc.yaml file into a Procfile string.
//
// It takes a path to an app_desc.yaml file as input and returns a string
// representation of a Procfile.
func TransformToProcfile(descFilePath string) (string, error) {
	yamlFile, err := os.ReadFile(descFilePath)
	if err != nil {
		return "", err
	}

	desc := AppDesc{}
	if err = yaml.Unmarshal(yamlFile, &desc); err != nil {
		return "", err
	}

	lines := []string{}
	for pType, p := range desc.Module.Processes {
		lines = append(lines, fmt.Sprintf("%s: %s", pType, p.Command))
	}

	return strings.Join(lines, "\n"), nil
}
