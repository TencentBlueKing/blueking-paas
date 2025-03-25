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
}{Viper: viper.New()}

// SetGlobalConfig set global config
func SetGlobalConfig() {
	G.BindPFlags(pflag.CommandLine)
	G.AutomaticEnv()

	G.SourceURL = G.GetString("source-url")
	G.DestURL = G.GetString("dest-url")

	G.SetDefault("RUNTIME", "pind")
	G.Runtime = G.GetString("RUNTIME")
	G.SetDefault("RUNTIME_WORKSPACE", "/podman/smart-app")
	G.RuntimeWorkspace = G.GetString("RUNTIME_WORKSPACE")
	G.DaemonSockFile = G.GetString("DAEMON_SOCK")

	G.SetDefault("CNB_BUILDER_IMAGE", "bk-builder-heroku-bionic:v1.0.2")
	G.CNBBuilderImage = G.GetString("CNB_BUILDER_IMAGE")
	G.CNBRunImageTAR = G.GetString("CNB_RUN_IMAGE_TAR")
	G.CNBRunImage = G.GetString("CNB_RUN_IMAGE")

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
	G.SetDefault("GO_BUILDPACK_VERSION", "v191")
	G.SetDefault("GO_BUCKET_URL", "https://bkpaas-runtimes-1252002024.file.myqcloud.com/golang")

	// set bk-buildpack-apt env
	G.SetDefault("APT_BUILDPACK_VERSION", "v2")
}
