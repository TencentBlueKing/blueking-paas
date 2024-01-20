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

package launch

import (
	"os"
	"os/exec"

	"gopkg.in/yaml.v3"
)

// DefaultAppDir ...
const DefaultLifecycleDir = "/lifecycle"

// AppDesc ...
type AppDesc struct {
	SpecVersion string `yaml:"spec_version"`
	Module      struct {
		Scripts struct {
			PreReleaseHook string `yaml:"pre_release_hook"`
		} `yaml:"scripts"`
	} `yaml:"module"`
}

func runPreReleaseHook() error {
	releaseHook, err := parsePreReleaseHook()
	if err != nil {
		return err
	}

	if releaseHook == "" {
		return nil
	}

	cmd := exec.Command(DefaultLifecycleDir+"/launcher", releaseHook)

	cmd.Dir = DefaultAppDir
	cmd.Env = os.Environ()
	cmd.Stderr = os.Stderr
	cmd.Stdout = os.Stdout

	if err = cmd.Run(); err != nil {
		return err
	}

	return nil
}

func parsePreReleaseHook() (string, error) {
	yamlFile, err := os.ReadFile(DefaultAppDir + "/app_desc.yaml")
	if err != nil {
		return "", err
	}

	desc := AppDesc{}
	if err = yaml.Unmarshal(yamlFile, &desc); err != nil {
		return "", err
	}

	return desc.Module.Scripts.PreReleaseHook, nil
}
