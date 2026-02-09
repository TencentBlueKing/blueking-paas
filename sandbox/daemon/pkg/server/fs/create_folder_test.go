package fs

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"

	"github.com/gin-gonic/gin"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/httputil"
)

var _ = Describe("CreateFolder", func() {
	var (
		router *gin.Engine
		w      *httptest.ResponseRecorder
		tmpDir string

		url string
	)

	BeforeEach(func() {
		gin.SetMode(gin.TestMode)

		url = "/files/folder"

		var err error
		tmpDir, err = os.MkdirTemp("", "create-folder-test-*")
		Expect(err).NotTo(HaveOccurred())

		router = gin.New()
		router.Use(httputil.ErrorMiddleware())
		router.POST(url, CreateFolder)

		w = httptest.NewRecorder()
	})

	AfterEach(func() {
		if tmpDir != "" {
			os.RemoveAll(tmpDir) // nolint
		}
	})

	Context("create folder", func() {
		It("should create folder with default permissions", func() {
			testDir := filepath.Join(tmpDir, "newdir")

			body := map[string]string{"path": testDir}
			jsonBody, _ := json.Marshal(body)
			req, _ := http.NewRequest("POST", url, bytes.NewBuffer(jsonBody))
			req.Header.Set("Content-Type", "application/json")
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusCreated))

			info, err := os.Stat(testDir)
			Expect(err).NotTo(HaveOccurred())
			Expect(info.IsDir()).To(BeTrue())

			Expect(info.Mode().Perm()).To(Equal(os.FileMode(0o755)))
		})

		It("should create folder with custom permissions", func() {
			testDir := filepath.Join(tmpDir, "customdir")

			body := map[string]string{"path": testDir, "mode": "0700"}
			jsonBody, _ := json.Marshal(body)
			req, _ := http.NewRequest("POST", url, bytes.NewBuffer(jsonBody))
			req.Header.Set("Content-Type", "application/json")
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusCreated))

			info, err := os.Stat(testDir)
			Expect(err).NotTo(HaveOccurred())
			Expect(info.IsDir()).To(BeTrue())

			Expect(info.Mode().Perm()).To(Equal(os.FileMode(0o700)))
		})

		It("should create nested folders", func() {
			testDir := filepath.Join(tmpDir, "parent", "child", "grandchild")

			body := map[string]string{"path": testDir}
			jsonBody, _ := json.Marshal(body)
			req, _ := http.NewRequest("POST", url, bytes.NewBuffer(jsonBody))
			req.Header.Set("Content-Type", "application/json")
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusCreated))

			info, err := os.Stat(testDir)
			Expect(err).NotTo(HaveOccurred())
			Expect(info.IsDir()).To(BeTrue())

			parentInfo, err := os.Stat(filepath.Join(tmpDir, "parent"))
			Expect(err).NotTo(HaveOccurred())
			Expect(parentInfo.IsDir()).To(BeTrue())
		})

		It("should handle existing directory", func() {
			testDir := filepath.Join(tmpDir, "existingdir")

			err := os.Mkdir(testDir, 0o755)
			Expect(err).NotTo(HaveOccurred())

			body := map[string]string{"path": testDir}
			jsonBody, _ := json.Marshal(body)
			req, _ := http.NewRequest("POST", url, bytes.NewBuffer(jsonBody))
			req.Header.Set("Content-Type", "application/json")
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusCreated))
		})
	})

	Context("parameter validation", func() {
		It("should reject request without path parameter", func() {
			body := map[string]string{}
			jsonBody, _ := json.Marshal(body)
			req, _ := http.NewRequest("POST", url, bytes.NewBuffer(jsonBody))
			req.Header.Set("Content-Type", "application/json")
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
		})

		It("should reject empty path parameter", func() {
			body := map[string]string{"path": ""}
			jsonBody, _ := json.Marshal(body)
			req, _ := http.NewRequest("POST", url, bytes.NewBuffer(jsonBody))
			req.Header.Set("Content-Type", "application/json")
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
		})

		It("should reject invalid mode format", func() {
			testDir := filepath.Join(tmpDir, "testdir")

			body := map[string]string{"path": testDir, "mode": "invalid"}
			jsonBody, _ := json.Marshal(body)
			req, _ := http.NewRequest("POST", url, bytes.NewBuffer(jsonBody))
			req.Header.Set("Content-Type", "application/json")
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
			Expect(w.Body.String()).To(ContainSubstring("invalid mode format"))
		})

		It("should handle decimal mode value", func() {
			testDir := filepath.Join(tmpDir, "testdir")

			body := map[string]string{"path": testDir, "mode": "755"}
			jsonBody, _ := json.Marshal(body)
			req, _ := http.NewRequest("POST", url, bytes.NewBuffer(jsonBody))
			req.Header.Set("Content-Type", "application/json")
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusCreated))

			info, err := os.Stat(testDir)
			Expect(err).NotTo(HaveOccurred())
			Expect(info.Mode().Perm()).To(Equal(os.FileMode(0o755)))
		})

		It("should handle various permission modes", func() {
			testCases := []struct {
				mode     string
				expected os.FileMode
			}{
				{"0755", 0o755},
				{"0700", 0o700},
				{"0644", 0o644},
			}

			for _, tc := range testCases {
				testDir := filepath.Join(tmpDir, "testdir-"+tc.mode)

				body := map[string]string{"path": testDir, "mode": tc.mode}
				jsonBody, _ := json.Marshal(body)
				req, _ := http.NewRequest("POST", url, bytes.NewBuffer(jsonBody))
				req.Header.Set("Content-Type", "application/json")
				w = httptest.NewRecorder()
				router.ServeHTTP(w, req)

				Expect(w.Code).To(Equal(http.StatusCreated))

				info, err := os.Stat(testDir)
				Expect(err).NotTo(HaveOccurred())
				Expect(info.Mode().Perm()).To(Equal(tc.expected))
			}
		})
	})

	Context("error handling", func() {
		It("should handle invalid path", func() {
			invalidPath := string([]byte{0x00})

			body := map[string]string{"path": invalidPath}
			jsonBody, _ := json.Marshal(body)
			req, _ := http.NewRequest("POST", url, bytes.NewBuffer(jsonBody))
			req.Header.Set("Content-Type", "application/json")
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
		})
	})
})
