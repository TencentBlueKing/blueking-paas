package utils

import (
	"os"
	"os/exec"
)

// Command returns a new command which writes its output to os.Stdout and stderr to os.Stderr
func Command(name string, args ...string) *exec.Cmd {
	cmd := exec.Command(name, args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd
}
