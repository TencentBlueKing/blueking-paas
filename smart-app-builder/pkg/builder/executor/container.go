/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *     http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

package executor

import (
	"bufio"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	"github.com/go-logr/logr"
	"github.com/pkg/errors"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/config"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/plan"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/utils"
)

// containerExecutor is a build executor in container
type containerExecutor struct {
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

// GetAppDir returns the source code directory
func (c *containerExecutor) GetAppDir() string {
	return c.sourceDir
}

// Build will build the source code by plan, return the artifact({app_code}.tgz) file path
func (c *containerExecutor) Build(buildPlan *plan.BuildPlan) (string, error) {
	if err := c.startDaemon(); err != nil {
		return "", errors.Wrap(err, "starting daemon")
	}

	runImage, err := c.loadRunImage()
	if err != nil {
		return "", errors.Wrap(err, "loading run image")
	}

	if err = c.runBuilder(buildPlan, runImage); err != nil {
		return "", errors.Wrap(err, "running builder")
	}

	if err = c.saveImages(buildPlan); err != nil {
		return "", errors.Wrap(err, "save images")
	}

	artifactTGZ, err := archiveArtifactTarball(buildPlan, c.destDir)
	if err != nil {
		return "", errors.Wrap(err, "building artifact tarball")
	}
	return artifactTGZ, nil
}

func (c *containerExecutor) mkWorkspaces() error {
	for _, dir := range []string{c.sourceDir, c.destDir, c.tmpDir} {
		if err := os.MkdirAll(dir, 0o744); err != nil {
			return err
		}
	}
	return nil
}

func (c *containerExecutor) startDaemon() error {
	if err := c.cmdProvider.StartDaemon().Start(); err != nil {
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

	return errors.Errorf("daemon not ready in %d seconds", retryCount)
}

func (c *containerExecutor) loadRunImage() (string, error) {
	if err := c.cmdProvider.LoadImage(config.G.CNBRunImageTAR).Run(); err != nil {
		return "", err
	}
	return config.G.CNBRunImage, nil
}

// runBuilder run cnb builder with runImage
func (c *containerExecutor) runBuilder(buildPlan *plan.BuildPlan, runImage string) error {
	for _, group := range buildPlan.BuildGroups {
		// 1. 制作 source.tgz 模块源码包
		moduleSrcDir := filepath.Join(c.sourceDir, group.SourceDir)
		moduleSrcTGZ := filepath.Join(c.tmpDir, group.BuildModuleName, "source.tgz")

		var procfile map[string]string
		if buildPlan.PackagingVersion == "v1" {
			// v1 旧方案: 每个模块使用自己的 Procfile, 不包含模块名前缀
			procfile = buildPlan.GenerateProcfileForModule(group.BuildModuleName)
		} else {
			// v2 新方案: 使用统一的 Procfile, 包含 "模块名-进程名" 格式
			procfile = buildPlan.GenerateProcfile()
		}

		if err := archiveSourceTarball(moduleSrcDir, moduleSrcTGZ, procfile); err != nil {
			return err
		}

		// 2. 生成运行命令参数
		args := makeRunArgs(buildPlan.AppCode, group, moduleSrcTGZ, runImage)
		c.logger.Info("build", "module name", group.BuildModuleName, "run args", args)

		// 3. 运行构建命令, 并打印输出
		cmd := c.cmdProvider.RunImage(config.G.CNBBuilderImage, args...)

		stdout, _ := cmd.StdoutPipe()
		cmd.Stderr = cmd.Stdout

		if err := cmd.Start(); err != nil {
			return err
		}

		go func() {
			scanner := bufio.NewScanner(stdout)
			for scanner.Scan() {
				c.logger.Info(scanner.Text())
			}
		}()

		if err := cmd.Wait(); err != nil {
			return err
		}
	}

	return nil
}

func (c *containerExecutor) saveImages(buildPlan *plan.BuildPlan) error {
	for _, group := range buildPlan.BuildGroups {
		cmd := c.cmdProvider.SaveImage(
			group.OutputImage,
			filepath.Join(c.destDir, group.OutputImageTarName),
		)

		if err := cmd.Run(); err != nil {
			return err
		}
	}
	return nil
}

// CommandProvider is the interface of command provider
type CommandProvider interface {
	// StartDaemon returns the command to start container daemon
	StartDaemon() *exec.Cmd
	// LoadImage returns the command to load tar to image
	LoadImage(tar string) *exec.Cmd
	// SaveImage returns the command to save image
	SaveImage(image string, destTAR string) *exec.Cmd
	// RunImage returns the command to run image
	RunImage(image string, args ...string) *exec.Cmd
}

// NewContainerExecutor return a container executor to build app.
// It supports pind and dind, if not set, default is pind.
func NewContainerExecutor() (*containerExecutor, error) {
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

	r := &containerExecutor{
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
