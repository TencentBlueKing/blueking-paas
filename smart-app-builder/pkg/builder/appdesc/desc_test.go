package appdesc_test

import (
	"os"
	"path/filepath"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueking/bkpaas/smart-app-builder/pkg/builder/appdesc"
)

var _ = Describe("ParseAppDescYAML", func() {
	var yamlDir string
	var yamlPath string

	BeforeEach(func() {
		yamlDir, _ = os.MkdirTemp("", "tmp")
		yamlPath = filepath.Join(yamlDir, "app_desc.yaml")
	})
	AfterEach(func() {
		Expect(os.RemoveAll(yamlDir)).To(BeNil())
	})

	It("parse app desc v2", func() {
		content := []byte(`spec_version: 2
app_version: 1.0.0
app:
  bk_app_code: test-app-code
modules:
  default:
    language: python
    processes:
      web:
        command: python main.py
  backend:
    language: go
    processes:
      api-process:
        command: go run main.go`)

		Expect(os.WriteFile(yamlPath, content, 0o644)).To(BeNil())
		appDesc, err := appdesc.ParseAppDescYAML(yamlPath)
		Expect(err).To(BeNil())
		Expect(appDesc.GetAppCode()).To(Equal("test-app-code"))

		procfile := appDesc.GenerateProcfile()
		Expect(procfile["default-web"]).To(Equal("python main.py"))
		Expect(procfile["backend-api-process"]).To(Equal("go run main.go"))
	})

	It("parse app desc v3", func() {
		content := []byte(`specVersion: 3
appVersion: 1.0.0
app:
  bkAppCode: test-app-code
modules:
  - name: web
    language: python
    spec:
      processes:
        - name: web-process
          procCommand: python main.py
  - name: api
    language: go
    sourceDir: backend
    spec:
      processes:
        - name: api-process
          procCommand: go run main.go`)

		Expect(os.WriteFile(yamlPath, content, 0o644)).To(BeNil())
		appDesc, err := appdesc.ParseAppDescYAML(yamlPath)
		Expect(err).To(BeNil())
		Expect(appDesc.GetAppCode()).To(Equal("test-app-code"))

		procfile := appDesc.GenerateProcfile()
		Expect(procfile["api-api-process"]).To(Equal("go run main.go"))
		Expect(procfile["web-web-process"]).To(Equal("python main.py"))
	})

	It("parse invalid spec version", func() {
		content := []byte(`spec_version: 1
app_version: 1.0.0`)

		Expect(os.WriteFile(yamlPath, content, 0o644)).To(BeNil())
		_, err := appdesc.ParseAppDescYAML(yamlPath)
		Expect(err).NotTo(BeNil())
	})
})
