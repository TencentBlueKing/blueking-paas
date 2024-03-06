package phase

import (
	"os/exec"
	"syscall"
)

const (
	linuxContainerAdmin = 0
)

// CmdOptsProvider opts for exec.Cmd
type CmdOptsProvider func(cmd *exec.Cmd)

// WithRoot set the cmd caller as root
func WithRoot() CmdOptsProvider {
	return func(cmd *exec.Cmd) {
		if cmd.SysProcAttr == nil {
			cmd.SysProcAttr = &syscall.SysProcAttr{}
		}
		cmd.SysProcAttr.Credential = &syscall.Credential{
			Uid:         linuxContainerAdmin,
			Gid:         linuxContainerAdmin,
			Groups:      nil,
			NoSetGroups: false,
		}
	}
}

// WithUser set the cmd caller as given uid, gid
func WithUser(uid, gid uint32) CmdOptsProvider {
	return func(cmd *exec.Cmd) {
		if cmd.SysProcAttr == nil {
			cmd.SysProcAttr = &syscall.SysProcAttr{}
		}
		cmd.SysProcAttr.Credential = &syscall.Credential{
			Uid:         uid,
			Gid:         gid,
			Groups:      nil,
			NoSetGroups: false,
		}
	}
}

// WithEnv set the cmd env
func WithEnv(env []string) CmdOptsProvider {
	return func(cmd *exec.Cmd) {
		cmd.Env = env
	}
}
