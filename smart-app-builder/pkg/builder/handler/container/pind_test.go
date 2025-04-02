package container

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("PindCmdProvider", func() {
	pindCommandProvider := pindCmdProvider{
		execPath: "podman",
	}

	It("StartDaemonCmd", func() {
		cmd := pindCommandProvider.StartDaemonCmd()
		Expect(cmd.Args).To(Equal([]string{"podman", "system", "service", "--time", "0"}))
	})

	It("LoadImageCmd", func() {
		cmd := pindCommandProvider.LoadImageCmd("/tmp/test.tar")
		Expect(
			cmd.Args,
		).To(Equal([]string{"podman", "load", "-i", "/tmp/test.tar"}))
	})

	It("SaveImageCmd", func() {
		cmd := pindCommandProvider.SaveImageCmd("test:latest", "/tmp/test.tar")
		Expect(
			cmd.Args,
		).To(Equal([]string{"podman", "save", "-o", "/tmp/test.tar", "--format", "oci-archive", "test:latest"}))
	})

	It("RunImage", func() {
		cmd := pindCommandProvider.RunImage("test:latest", "echo", "hello")
		Expect(
			cmd.Args,
		).To(Equal([]string{"podman", "run", "echo", "hello", "test:latest"}))
	})
})
