package container

import (
	"os/exec"

	"github.com/pkg/errors"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/utils"
)

// pindCmdProvider podman-in-docker command provider
type pindCmdProvider struct {
	execPath string
}

// StartDaemonCmd start container daemon
func (p *pindCmdProvider) StartDaemonCmd() *exec.Cmd {
	return utils.Command(p.execPath, "system", "service", "--time", "0")
}

// LoadImageCmd load tar to image
func (p *pindCmdProvider) LoadImageCmd(tar string) *exec.Cmd {
	return utils.Command(p.execPath, "load", "-i", tar)
}

// SaveImageCmd save image
func (p *pindCmdProvider) SaveImageCmd(image string, destTAR string) *exec.Cmd {
	return utils.Command(p.execPath, "save", "-o", destTAR, "--format", "oci-archive", image)
}

// RunImage run image
func (p *pindCmdProvider) RunImage(image string, args ...string) *exec.Cmd {
	runArgs := []string{"run"}
	runArgs = append(runArgs, args...)
	runArgs = append(runArgs, image)
	return exec.Command(p.execPath, runArgs...)
}

// NewPindCmdProvider new pind command provider
func NewPindCmdProvider() (*pindCmdProvider, error) {
	execPath, err := exec.LookPath("podman")
	if err != nil {
		return nil, errors.New("podman command not found")
	}
	return &pindCmdProvider{execPath: execPath}, nil
}
