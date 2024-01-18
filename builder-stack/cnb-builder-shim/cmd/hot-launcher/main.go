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

package main

import (
	"os"
	"github.com/BurntSushi/toml"
	"github.com/buildpacks/lifecycle/launch"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/logging"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/utils"
	hotlaunch "github.com/TencentBlueking/bkpaas/cnb-builder-shim/cmd/hot-launcher/launch"
)

func main() {
	logger := logging.Default()

	var md launch.Metadata

	if _, err := toml.DecodeFile(launch.GetMetadataFilePath(utils.EnvOrDefault("CNB_LAYERS_DIR", "/layers")), &md); err != nil {
		logger.Error(err, "read metadata")
		os.Exit(1)
	}

	if err := hotlaunch.Run(&md); err != nil {
		logger.Error(err, "hot launch")
		os.Exit(1)
	}
	//headers, err := symlinkProcessLauncher(&md)
	//if err != nil {
	//	logger.Error(err, "symlink process launcher")
	//	os.Exit(1)
	//}
	//
	//if err = hotReloadProcesses(headers); err != nil {
	//	logger.Error(err, "hot reload processes")
	//	os.Exit(1)
	//}

}

//
//func symlinkProcessLauncher(md *launch.Metadata) ([]*tar.Header, error) {
//	hdrs := []*tar.Header{}
//	if len(md.Processes) > 0 {
//		for _, proc := range md.Processes {
//			if len(proc.Type) == 0 {
//				return nil, errors.New("type is required for all processes")
//			}
//			if err := validateProcessType(proc.Type); err != nil {
//				return nil, errors.Wrapf(err, "invalid process type '%s'", proc.Type)
//			}
//			hdrs = append(hdrs, typeSymlink(launch.ProcessPath(proc.Type)))
//		}
//
//		if err := createPath(launch.ProcessDir); err != nil {
//			return nil, err
//		}
//
//		for _, hdr := range hdrs {
//			if err := createSymlink(hdr); err != nil {
//				return nil, errors.Wrapf(err, "failed to create symlink %q with target %q", hdr.Name, hdr.Linkname)
//			}
//		}
//	}
//	return hdrs, nil
//}
//
//func hotReloadProcesses(hdrs []*tar.Header) error {
//
//	return nil
//}
//
//func validateProcessType(pType string) error {
//	forbiddenCharacters := `/><:|&\`
//	if strings.ContainsAny(pType, forbiddenCharacters) {
//		return fmt.Errorf(`type may not contain characters '%s'`, forbiddenCharacters)
//	}
//	return nil
//}
//
//func typeSymlink(path string) *tar.Header {
//	return &tar.Header{
//		Typeflag: tar.TypeSymlink,
//		Name:     path,
//		Linkname: launch.LauncherPath,
//		Mode:     modePerm,
//	}
//}
//
//func createSymlink(hdr *tar.Header) error {
//	if _, err := os.Stat(hdr.Name); os.IsNotExist(err) {
//		return os.Symlink(hdr.Linkname, hdr.Name)
//	}
//	return nil
//}
//
//func createPath(dir string) error {
//	if _, err := os.Stat(dir); os.IsNotExist(err) {
//		return os.Mkdir(dir, os.FileMode(modePerm))
//	}
//	return nil
//}
