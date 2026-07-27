package main

import (
	"bytes"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("daemon command", func() {
	It("registers version and resident as subcommands", func() {
		rootCmd := newRootCommand()
		commandNames := make([]string, 0, len(rootCmd.Commands()))
		for _, command := range rootCmd.Commands() {
			commandNames = append(commandNames, command.Name())
		}

		Expect(rootCmd.CommandPath()).To(Equal("daemon"))
		Expect(commandNames).To(ConsistOf("resident", "version"))
	})

	It("prints version information through the version subcommand", func() {
		rootCmd := newRootCommand()
		output := new(bytes.Buffer)
		rootCmd.SetOut(output)
		rootCmd.SetArgs([]string{"version"})

		Expect(rootCmd.Execute()).To(Succeed())
		Expect(output.String()).To(Equal("version: " + version + "\nbuildTime: " + buildTime + "\n"))
	})

	It("forwards arbitrary arguments to the root command", func() {
		var receivedArgs []string
		rootCmd := newRootCommandWithSandboxRunner(func(args []string) {
			receivedArgs = args
		})
		rootCmd.SetArgs([]string{"start", "web", "--port", "8080"})

		Expect(rootCmd.Execute()).To(Succeed())
		Expect(receivedArgs).To(Equal([]string{"start", "web", "--port", "8080"}))
	})

	It("forwards entrypoint flags and their values to the root command", func() {
		var receivedArgs []string
		rootCmd := newRootCommandWithSandboxRunner(func(args []string) {
			receivedArgs = args
		})
		rootCmd.SetArgs([]string{"--mode", "version"})

		Expect(rootCmd.Execute()).To(Succeed())
		Expect(receivedArgs).To(Equal([]string{"--mode", "version"}))
	})
})
