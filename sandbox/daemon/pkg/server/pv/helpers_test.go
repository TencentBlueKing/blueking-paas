package pv

import (
	"os"
	"path/filepath"

	"github.com/gin-gonic/gin"
	"github.com/gin-gonic/gin/binding"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/config"
	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/httputil"
)

const testBasePath = "app/volume1"

// newTestEnv points config.G at a fresh temp storage root, creates the jail root
// (rootDir/testBasePath), and returns both so specs can drop fixture files in.
func newTestEnv() (rootDir, jailRoot string) {
	rootDir, err := os.MkdirTemp("", "pv-handler-*")
	if err != nil {
		panic(err)
	}
	config.G = &config.Config{
		RootDir:         rootDir,
		PreviewMaxBytes: 65536,
		ArchiveMaxSize:  100 * 1024 * 1024,
	}
	jailRoot = filepath.Join(rootDir, testBasePath)
	if err := os.MkdirAll(jailRoot, 0o755); err != nil {
		panic(err)
	}
	return rootDir, jailRoot
}

// newTestRouter builds a gin engine with the error middleware and validator wired,
// matching the resident server setup minus auth.
func newTestRouter() *gin.Engine {
	gin.SetMode(gin.TestMode)
	binding.Validator = new(httputil.DefaultValidator)
	r := gin.New()
	r.Use(httputil.ErrorMiddleware())
	return r
}

var _ = Describe("detectMimeByExt", func() {
	DescribeTable("infers mime by extension",
		func(name, expected string) {
			Expect(detectMimeByExt(name)).To(Equal(expected))
		},
		Entry("plain text", "a.txt", "text/plain"),
		Entry("log", "app.log", "text/plain"),
		Entry("markdown", "README.md", "text/markdown"),
		Entry("yaml", "config.yaml", "application/yaml"),
		Entry("toml", "config.toml", "application/toml"),
		Entry("csv", "data.csv", "text/csv"),
		Entry("go", "main.go", "text/x-go"),
		Entry("python", "app.py", "text/x-python"),
		Entry("sql", "schema.sql", "application/sql"),
		// 大写扩展名归一化
		Entry("upper-case ext", "README.MD", "text/markdown"),
		// 标准库内置表覆盖的类型
		Entry("html", "report.html", "text/html"),
		Entry("json", "data.json", "application/json"),
		Entry("svg", "logo.svg", "image/svg+xml"),
		// 未知扩展名兜底
		Entry("unknown ext", "blob.xyz", "application/octet-stream"),
		Entry("no ext", "Makefile", "application/octet-stream"),
	)
})
