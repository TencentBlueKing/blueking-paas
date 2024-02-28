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
	"fmt"
	"os"
	"os/exec"
	"strings"

	"github.com/buildpacks/lifecycle/launch"
	"github.com/pkg/errors"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/appdesc"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/utils"
)

var DefaultAppDir = utils.EnvOrDefault("CNB_APP_DIR", "/app")

// Process is a process to launch
type Process struct {
	ProcType    string
	CommandPath string
}

// metaProcesses is a list of launch.Process. meta prefix is inspired from lifecycle Metadata
type metaProcesses []launch.Process

// Run launches the given launch.Process list and app desc.
func Run(mdProcesses metaProcesses, desc *appdesc.AppDesc) error {
	processes, err := symlinkProcessLauncher(mdProcesses)
	if err != nil {
		return errors.Wrap(err, "symlink process launcher")
	}

	if err = runPreReleaseHook(desc); err != nil {
		return errors.Wrap(err, "run pre release hook")
	}

	if err = reloadProcesses(processes, desc); err != nil {
		return errors.Wrap(err, "reload processes")
	}

	return nil
}

// symlinkProcessLauncher creates symbolic links for the given launch.Process list.
//
// It takes in a slice of launch.Process and returns a slice of Process and an error.
//
// how symlink created from mdProcesses{web, worker}:
//
//	web process will create symlink like "/cnb/process/web -> /cnb/lifecycle/launcher"
//	worker process will create symlink like "/cnb/process/worker -> /cnb/lifecycle/launcher"
func symlinkProcessLauncher(mdProcesses metaProcesses) ([]Process, error) {
	processes := []Process{}

	if len(mdProcesses) == 0 {
		return processes, errors.New("processes is required")
	}

	for _, proc := range mdProcesses {
		if len(proc.Type) == 0 {
			return processes, errors.New("type is required for all processes")
		}

		if err := validateProcessType(proc.Type); err != nil {
			return processes, errors.Wrapf(err, "invalid process type '%s'", proc.Type)
		}

		processes = append(processes, Process{ProcType: proc.Type, CommandPath: launch.ProcessPath(proc.Type)})

	}

	if err := os.MkdirAll(launch.ProcessDir, 0o755); err != nil {
		return processes, err
	}

	for _, p := range processes {
		if err := utils.CreateSymlink(launch.LauncherPath, p.CommandPath); err != nil {
			return processes, err
		}
	}

	return processes, nil
}

func runPreReleaseHook(desc *appdesc.AppDesc) error {
	releaseHook := desc.Module.Scripts.PreReleaseHook
	if releaseHook == "" {
		return nil
	}

	cmd := exec.Command(launch.LauncherPath, releaseHook)
	cmd.Dir = DefaultAppDir
	cmd.Stderr = os.Stderr
	cmd.Stdout = os.Stdout

	cmd.Env = os.Environ()
	if desc.Module.ProcEnvs != nil {
		for _, env := range desc.Module.ProcEnvs {
			cmd.Env = append(cmd.Env, fmt.Sprintf("%s=%s", env.Key, env.Value))
		}
	}

	return cmd.Run()
}

func reloadProcesses(processes []Process, appDesc *appdesc.AppDesc) error {
	ctl := NewSupervisorCtl()

	var conf *SupervisorConf

	if appDesc.Module.ProcEnvs != nil {
		conf = MakeSupervisorConf(processes, appDesc.Module.ProcEnvs...)
	} else {
		conf = MakeSupervisorConf(processes)
	}

	return ctl.Reload(conf)
}

// validateProcessType func copy from github.com/buildpacks/lifecycle
func validateProcessType(pType string) error {
	forbiddenCharacters := `/><:|&\`
	if strings.ContainsAny(pType, forbiddenCharacters) {
		return fmt.Errorf(`type may not contain characters '%s'`, forbiddenCharacters)
	}
	return nil
}
