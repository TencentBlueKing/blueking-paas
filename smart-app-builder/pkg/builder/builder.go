package builder

import (
	"net/url"
	"os"
	"path/filepath"

	"github.com/pkg/errors"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/fetcher/fs"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/fetcher/http"
	"github.com/go-logr/logr"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/utils"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/plan"
	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/executor"
)

// AppBuilder build the source code to artifact
type AppBuilder struct {
	sourceURL string
	destURL   string
	exec      BuildExecutor

	logger logr.Logger
}

// Build run build process
func (a *AppBuilder) Build() error {
	appDir := a.exec.GetAppDir()

	// 获取源码
	if err := a.fetchSource(appDir); err != nil {
		return err
	}

	// 准备构建计划
	buildPlan, err := plan.PrepareBuildPlan(appDir)
	if err != nil {
		return err
	}

	// 执行构建, 生成 artifact
	artifactTGZ, err := a.exec.Build(buildPlan)
	if err != nil {
		return err
	}

	return a.pushArtifact(artifactTGZ)
}

// fetchSource fetch the source code to destDir
func (a *AppBuilder) fetchSource(destDir string) error {
	parsedURL, err := url.Parse(a.sourceURL)
	if err != nil {
		return err
	}

	switch parsedURL.Scheme {
	case "file":
		// TODO 重构 cnb-builder-shim/pkg/fetcher/fs 以支持非压缩文件, 简化此处代码
		filePath := parsedURL.Path

		fileInfo, err := os.Stat(filePath)
		if err != nil {
			return err
		}

		if !fileInfo.IsDir() {
			if err = fs.NewFetcher(a.logger).Fetch(filePath, destDir); err != nil {
				return err
			} else {
				return nil
			}
		}

		// 如果是文件目录, 目录不同时, 直接将源码拷贝到 destDir 下
		if filePath != destDir {
			return utils.CopyDir(filePath, destDir)
		}
		return nil

	case "http", "https":
		if err := http.NewFetcher(a.logger).Fetch(a.sourceURL, destDir); err != nil {
			return err
		}
	default:
		return errors.Errorf("not support source-url scheme: %s", parsedURL.Scheme)
	}

	return nil
}

func (a *AppBuilder) pushArtifact(artifactTGZ string) error {
	parsedURL, err := url.Parse(a.destURL)
	if err != nil {
		return err
	}

	switch parsedURL.Scheme {
	case "file":
		filePath := parsedURL.Path

		fileName := filepath.Base(filePath)
		if filepath.Ext(fileName) == ".tgz" {
			if err = os.MkdirAll(filepath.Dir(filePath), 0o744); err != nil {
				return err
			}
			return utils.CopyFile(artifactTGZ, filePath)
		}

		// 假定 filePath 是目录处理, 否则出错
		if err = os.MkdirAll(filePath, 0o744); err != nil {
			return err
		}
		return utils.CopyFile(artifactTGZ, filepath.Join(filePath, filepath.Base(artifactTGZ)))

	default:
		// TODO push to bkrepo
		return errors.Errorf("not support dest-url scheme: %s", parsedURL.Scheme)
	}
}

// BuildExecutor is the interface which execute the build process
type BuildExecutor interface {
	// GetAppDir return the source code directory
	GetAppDir() string
	// Build will build the source code by plan, return the artifact({app_code}.tgz) file path
	Build(buildPlan *plan.BuildPlan) (string, error)
}

// New returns a AppBuilder instance
func New(logger logr.Logger, sourceURL, destURL string) (*AppBuilder, error) {
	if exec, err := executor.NewContainerExecutor(); err != nil {
		return nil, err
	} else {
		return &AppBuilder{logger: logger, sourceURL: sourceURL, destURL: destURL, exec: exec}, nil
	}
}
