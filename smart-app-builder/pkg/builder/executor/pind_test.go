package executor

import (
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("PindCmdProvider", func() {
	pindCommandProvider := pindCmdProvider{
		execPath: "podman",
	}

	It("StartDaemon", func() {
		cmd := pindCommandProvider.StartDaemon()
		Expect(cmd.Args).To(Equal([]string{"podman", "system", "service", "--time", "0"}))
	})

	It("LoadImage", func() {
		cmd := pindCommandProvider.LoadImage("/tmp/test.tar")
		Expect(
			cmd.Args,
		).To(Equal([]string{"podman", "load", "-i", "/tmp/test.tar"}))
	})

	It("SaveImage", func() {
		cmd := pindCommandProvider.SaveImage("test:latest", "/tmp/test.tar")
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
