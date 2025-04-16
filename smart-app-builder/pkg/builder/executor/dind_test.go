package executor

import (
	"fmt"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/config"
)

var _ = Describe("DindCmdProvider", func() {
	// 设置全局配置
	config.SetGlobalConfig()

	unixSock := fmt.Sprintf("unix://%s", config.G.DaemonSockFile)
	dindCommandProvider := dindCmdProvider{
		execPath: "docker",
	}

	It("StartDaemon", func() {
		cmd := dindCommandProvider.StartDaemon()
		Expect(cmd.Args).To(Equal([]string{""}))
	})

	It("LoadImage", func() {
		cmd := dindCommandProvider.LoadImage("/tmp/test.tar")
		Expect(
			cmd.Args,
		).To(Equal([]string{"docker", "-H", unixSock, "load", "-i", "/tmp/test.tar"}))
	})

	It("SaveImage", func() {
		cmd := dindCommandProvider.SaveImage("test:latest", "/tmp/test.tar")
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
