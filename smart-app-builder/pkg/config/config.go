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

// Package config ...
package config

import (
	"github.com/spf13/pflag"
	"github.com/spf13/viper"
)

var G = struct {
	*viper.Viper

	// The url of the source code, which begins with file:// or http(s)://
	SourceURL string
	// The url of the s-mart artifact to put, which begins with file:// or http(s)://
	DestURL string

	// RuntimeWorkspace is runtime workspace
	RuntimeWorkspace string
	// Runtime is runtime. pind(podman-in-docker) or dind(docker-in-docker)
	Runtime string
	// DaemonSockFile is container daemon sock file
	DaemonSockFile string

	// CNBRunImageTAR is cnb run-scratch image tar path
	CNBRunImageTAR string
	// CNBRunImage is cnb run-scratch image
	CNBRunImage string
	// CNBBuilderImage is CNB builder image used to build the source code
	CNBBuilderImage string

	// BuildpackType is the type of buildpack to use. Supported values: oci-embedded and tgz, default is oci-embedded
	BuildpackType string

	// CacheRegistry is a registry used to cache image layers. e.g., mirrors.tencent.com/bkapps
	CacheRegistry string
	// RegistryAuth is the cache registry auth. e.g., '{"mirrors.tencent.com": "Basic xxx"}'
	RegistryAuth string
}{Viper: viper.New()}

// SetGlobalConfig set global config
func SetGlobalConfig() {
	_ = G.BindPFlags(pflag.CommandLine)
	G.AutomaticEnv()

	G.SourceURL = G.GetString("source-url")
	G.DestURL = G.GetString("dest-url")

	G.SetDefault("RUNTIME", "pind")
	G.Runtime = G.GetString("RUNTIME")
	G.SetDefault("RUNTIME_WORKSPACE", "/podman/smart-app")
	G.RuntimeWorkspace = G.GetString("RUNTIME_WORKSPACE")
	G.DaemonSockFile = G.GetString("DAEMON_SOCK")

	G.SetDefault("BUILDER_SHIM_IMAGE", "bk-builder-heroku-bionic:v1.0.2")
	G.CNBBuilderImage = G.GetString("BUILDER_SHIM_IMAGE")
	G.CNBRunImageTAR = G.GetString("CNB_RUN_IMAGE_TAR")
	G.CNBRunImage = G.GetString("CNB_RUN_IMAGE")

	G.SetDefault("BUILDPACK_TYPE", "oci-embedded")
	G.BuildpackType = G.GetString("BUILDPACK_TYPE")

	// set bk-buildpack-python env
	G.SetDefault("PYTHON_BUILDPACK_VERSION", "v213")
	G.SetDefault("PIP_VERSION", "20.2.3")
	G.SetDefault("DISABLE_COLLECTSTATIC", "1")
	G.SetDefault("BUILDPACK_S3_BASE_URL", "https://bkpaas-runtimes-1252002024.file.myqcloud.com/python")
	G.SetDefault("PIP_INDEX_URL", "https://mirrors.cloud.tencent.com/pypi/simple/")
	G.SetDefault("PIP_EXTRA_INDEX_URL", "https://mirrors.tencent.com/tencent_pypi/simple/")

	// set bk-buildpack-nodejs env
	G.SetDefault("NODEJS_BUILDPACK_VERSION", "v163")
	G.SetDefault(
		"STDLIB_FILE_URL",
		"https://bkpaas-runtimes-1252002024.file.myqcloud.com/common/buildpack-stdlib/bk-node/stdlib.sh",
	)
	G.SetDefault("S3_DOMAIN", "https://bkpaas-runtimes-1252002024.file.myqcloud.com/nodejs/node/release/linux-x64/")
	G.SetDefault("NPM_REGISTRY", "https://mirrors.tencent.com/npm/")

	// set bk-buildpack-go env
	G.SetDefault("GO_BUILDPACK_VERSION", "v205")
	G.SetDefault("GO_BUCKET_URL", "https://bkpaas-runtimes-1252002024.file.myqcloud.com/golang")

	// set bk-buildpack-apt env
	G.SetDefault("APT_BUILDPACK_VERSION", "v2")

	G.CacheRegistry = G.GetString("CACHE_REGISTRY")
	G.RegistryAuth = G.GetString("REGISTRY_AUTH")
}
