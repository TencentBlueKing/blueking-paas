package volumefs

import (
	"os"
	"path/filepath"

	"github.com/gin-gonic/gin"
	"github.com/gin-gonic/gin/binding"

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
		RootDir: rootDir,
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
