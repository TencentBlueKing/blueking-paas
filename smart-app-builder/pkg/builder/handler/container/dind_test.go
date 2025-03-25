package container

import (
	"fmt"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/config"
)

var _ = Describe("DindCmdProvider", func() {
	// 设置全局配置
	config.SetGlobalConfig()

	unixSock := fmt.Sprintf("unix://%s", config.G.DaemonSockFile)
	dindCommandProvider := dindCmdProvider{
		execPath: "docker",
	}

	It("StartDaemonCmd", func() {
		cmd := dindCommandProvider.StartDaemonCmd()
		Expect(cmd.Args).To(Equal([]string{""}))
	})

	It("LoadImageCmd", func() {
		cmd := dindCommandProvider.LoadImageCmd("/tmp/test.tar")
		Expect(
			cmd.Args,
		).To(Equal([]string{"docker", "-H", unixSock, "load", "-i", "/tmp/test.tar"}))
	})

	It("SaveImageCmd", func() {
		cmd := dindCommandProvider.SaveImageCmd("test:latest", "/tmp/test.tar")
		Expect(
			cmd.Args,
		).To(Equal([]string{"docker", "-H", unixSock, "save", "-o", "/tmp/test.tar", "test:latest"}))
	})

	It("RunImage", func() {
		cmd := dindCommandProvider.RunImage("test:latest", "echo", "hello")
		Expect(
			cmd.Args,
		).To(Equal([]string{"docker", "-H", unixSock, "run", "echo", "hello", "test:latest"}))
	})
})
