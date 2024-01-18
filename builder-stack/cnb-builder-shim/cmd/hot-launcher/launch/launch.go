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
	"strings"
	"fmt"
	"archive/tar"

	"github.com/buildpacks/lifecycle/launch"
	"github.com/pkg/errors"
)

// Run hot reload processes
func Run(md *launch.Metadata) error {
	headers, err := symlinkProcessLauncher(md)
	if err != nil {
		return errors.Wrap(err, "symlink process launcher")
	}

	if err = hotReloadProcesses(headers); err != nil {
		return errors.Wrap(err, "hot reload processes")
	}
	return nil
}

func symlinkProcessLauncher(md *launch.Metadata) ([]*tar.Header, error) {
	hdrs := []*tar.Header{}
	if len(md.Processes) > 0 {
		for _, proc := range md.Processes {
			if len(proc.Type) == 0 {
				return nil, errors.New("type is required for all processes")
			}
			if err := validateProcessType(proc.Type); err != nil {
				return nil, errors.Wrapf(err, "invalid process type '%s'", proc.Type)
			}
			hdrs = append(hdrs, typeSymlink(launch.ProcessPath(proc.Type)))
		}

		if err := createDir(launch.ProcessDir); err != nil {
			return nil, err
		}

		for _, hdr := range hdrs {
			if err := createSymlink(hdr.Linkname, hdr.Name); err != nil {
				return nil, errors.Wrapf(err, "failed to create symlink %q with target %q", hdr.Name, hdr.Linkname)
			}
		}
	}
	return hdrs, nil
}

func hotReloadProcesses(hdrs []*tar.Header) error {
	ctl := NewSupervisorCtl()

	processes := make([]Process, len(hdrs))
	for i, hdr := range hdrs {
		processes[i] = Process{
			ProcType: strings.TrimPrefix(hdr.Name, launch.ProcessDir+"/"),
			Command:  hdr.Linkname,
		}
	}

	conf := MakeSupervisorConf(processes)
	return ctl.Reload(conf)
}

func validateProcessType(pType string) error {
	forbiddenCharacters := `/><:|&\`
	if strings.ContainsAny(pType, forbiddenCharacters) {
		return fmt.Errorf(`type may not contain characters '%s'`, forbiddenCharacters)
	}
	return nil
}

func typeSymlink(path string) *tar.Header {
	var modePerm int64 = 0755
	return &tar.Header{
		Typeflag: tar.TypeSymlink,
		Name:     path,
		Linkname: launch.LauncherPath,
		Mode:     modePerm,
	}
}
