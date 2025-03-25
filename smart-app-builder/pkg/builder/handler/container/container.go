package container

import (
	"bufio"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	"github.com/go-logr/logr"
	"github.com/pkg/errors"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/config"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/plan"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/utils"
)

// runtimeHandler is a build handler in container runtime
type runtimeHandler struct {
	// cmdProvider is the command provider
	cmdProvider CommandProvider

	// sourceDir is the source code directory
	sourceDir string
	// destDir is the artifact directory
	destDir string
	// tmpDir is the tmp directory. The tmp directory is used to store saas module tgz
	tmpDir string

	logger logr.Logger
}

// GetAppDir return the source code directory
func (r *runtimeHandler) GetAppDir() string {
	return r.sourceDir
}

// Build will build the source code by plan, return the artifact({app_code}.tgz) file path
func (r *runtimeHandler) Build(buildPlan *plan.BuildPlan) (string, error) {
	if err := r.startDaemon(); err != nil {
		return "", errors.Wrap(err, "failed to start daemon")
	}

	runImage, err := r.loadRunImage()
	if err != nil {
		return "", errors.Wrap(err, "failed to load run image")
	}

	if err = r.runBuilder(buildPlan, runImage); err != nil {
		return "", errors.Wrap(err, "failed to run builder")
	}

	if err = r.saveImages(buildPlan); err != nil {
		return "", errors.Wrap(err, "failed to save images")
	}

	artifactTGZ, err := buildArtifactTarball(buildPlan, r.destDir)
	if err != nil {
		return "", errors.Wrap(err, "failed to build artifact tarball")
	}
	return artifactTGZ, nil
}

func (r *runtimeHandler) mkWorkspaces() error {
	for _, dir := range []string{r.sourceDir, r.destDir, r.tmpDir} {
		if err := os.MkdirAll(dir, 0o744); err != nil {
			return err
		}
	}
	return nil
}

func (r *runtimeHandler) startDaemon() error {
	if err := r.cmdProvider.StartDaemonCmd().Start(); err != nil {
		return err
	}

	sockFile := config.G.DaemonSockFile

	// 10 次重试, 探测 daemon 是否就绪
	retryCount := 10

	for i := 0; i < retryCount; i++ {
		if _, err := os.Stat(sockFile); err == nil {
			conn, connErr := net.Dial("unix", sockFile)
			if conn != nil {
				conn.Close()
			}
			if connErr == nil {
				return nil
			}
		}
		time.Sleep(1 * time.Second)
	}

	return errors.New("daemon not ready")
}

func (r *runtimeHandler) loadRunImage() (string, error) {
	if err := r.cmdProvider.LoadImageCmd(config.G.CNBRunImageTAR).Run(); err != nil {
		return "", err
	}
	return config.G.CNBRunImage, nil
}

// runBuilder run cnb builder with runImage
func (r *runtimeHandler) runBuilder(buildPlan *plan.BuildPlan, runImage string) error {
	for _, step := range buildPlan.Steps {
		// 1. 制作 source.tgz 模块源码包
		moduleSrcDir := filepath.Join(r.sourceDir, step.SourceDir)
		moduleSrcTGZ := filepath.Join(r.tmpDir, step.BuildModuleName, "source.tgz")
		if err := buildSourceTarball(moduleSrcDir, moduleSrcTGZ, buildPlan.Procfile); err != nil {
			return err
		}

		// 2. 构建运行命令参数
		args := buildRunArgs(step, moduleSrcTGZ, runImage)
		r.logger.Info("module name", step.BuildModuleName, "run args", args)

		// 3. 运行构建命令, 并打印输出
		cmd := r.cmdProvider.RunImage(config.G.CNBBuilderImage, args...)

		stdout, _ := cmd.StdoutPipe()
		cmd.Stderr = cmd.Stdout

		if err := cmd.Start(); err != nil {
			return err
		}

		go func() {
			scanner := bufio.NewScanner(stdout)
			for scanner.Scan() {
				r.logger.Info(scanner.Text())
			}
		}()

		if err := cmd.Wait(); err != nil {
			return err
		}
	}

	return nil
}

func (r *runtimeHandler) saveImages(buildPlan *plan.BuildPlan) error {
	for _, step := range buildPlan.Steps {
		cmd := r.cmdProvider.SaveImageCmd(
			step.OutPutImage,
			filepath.Join(r.destDir, step.OutPutImageTarName),
		)

		if err := cmd.Run(); err != nil {
			return err
		}
	}
	return nil
}

// CommandProvider is the interface of command provider
type CommandProvider interface {
	// StartDaemonCmd start container daemon
	StartDaemonCmd() *exec.Cmd
	// LoadImageCmd load tar to image
	LoadImageCmd(tar string) *exec.Cmd
	// SaveImageCmd save image
	SaveImageCmd(image string, destTAR string) *exec.Cmd
	// RunImage run image
	RunImage(image string, args ...string) *exec.Cmd
}

// NewRuntimeHandler return a new container runtime handler. It supports pind and dind, if not set, default is pind.
func NewRuntimeHandler() (*runtimeHandler, error) {
	var cmdProvider CommandProvider
	var err error

	if config.G.Runtime == "pind" {
		cmdProvider, err = NewPindCmdProvider()
	} else {
		cmdProvider, err = NewDindCmdProvider()
	}
	if err != nil {
		return nil, err
	}

	workspace := config.G.RuntimeWorkspace

	r := &runtimeHandler{
		cmdProvider: cmdProvider,
		sourceDir:   filepath.Join(workspace, "source"),
		destDir:     filepath.Join(workspace, "dest"),
		tmpDir:      filepath.Join(workspace, "tmp"),
		logger:      utils.GetLogger(),
	}

	if err = r.mkWorkspaces(); err != nil {
		return nil, err
	}

	return r, nil
}
