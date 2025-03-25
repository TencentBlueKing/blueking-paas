package container

import (
	"fmt"
	"os/exec"

	"github.com/pkg/errors"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/config"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/utils"
)

// dindCmdProvider docker-in-docker command provider
type dindCmdProvider struct {
	execPath string
}

// StartDaemonCmd start container daemon
func (d *dindCmdProvider) StartDaemonCmd() *exec.Cmd {
	execPath, _ := exec.LookPath("dockerd")
	return utils.Command(execPath)
}

// LoadImageCmd load tar to image
func (d *dindCmdProvider) LoadImageCmd(tar string) *exec.Cmd {
	return utils.Command(d.execPath, "-H", fmt.Sprintf("unix://%s", config.G.DaemonSockFile), "load", "-i", tar)
}

// SaveImageCmd save image
func (d *dindCmdProvider) SaveImageCmd(image string, destTAR string) *exec.Cmd {
	return utils.Command(
		d.execPath,
		"-H",
		fmt.Sprintf("unix://%s", config.G.DaemonSockFile),
		"save",
		"-o",
		destTAR,
		image,
	)
}

// RunImage run image
func (d *dindCmdProvider) RunImage(image string, args ...string) *exec.Cmd {
	runArgs := []string{"-H", fmt.Sprintf("unix://%s", config.G.DaemonSockFile), "run"}
	runArgs = append(runArgs, args...)
	runArgs = append(runArgs, image)
	return exec.Command(d.execPath, runArgs...)
}

// NewDindCmdProvider new dind command provider
func NewDindCmdProvider() (*dindCmdProvider, error) {
	execPath, err := exec.LookPath("docker")
	if err != nil {
		return nil, errors.New("docker command not found")
	}
	return &dindCmdProvider{execPath: execPath}, nil
}
