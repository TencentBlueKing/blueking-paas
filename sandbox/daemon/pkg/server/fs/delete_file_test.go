package fs

import (
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"

	"github.com/gin-gonic/gin"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/bkpaas/sandbox/daemon/pkg/server/httputil"
)

var _ = Describe("DeleteFile", func() {
	var (
		router *gin.Engine
		w      *httptest.ResponseRecorder
		tmpDir string
	)

	BeforeEach(func() {
		gin.SetMode(gin.TestMode)

		var err error
		tmpDir, err = os.MkdirTemp("", "delete-test-*")
		Expect(err).NotTo(HaveOccurred())

		router = gin.New()
		router.Use(httputil.ErrorMiddleware())
		router.DELETE("/files", DeleteFile)

		w = httptest.NewRecorder()
	})

	AfterEach(func() {
		if tmpDir != "" {
			os.RemoveAll(tmpDir) // nolint
		}
	})

	Context("delete regular file", func() {
		It("should delete existing file successfully", func() {
			testFile := filepath.Join(tmpDir, "test.txt")
			err := os.WriteFile(testFile, []byte("test content"), 0o644)
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("DELETE", "/files?path="+testFile, nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusNoContent))

			_, err = os.Stat(testFile)
			Expect(os.IsNotExist(err)).To(BeTrue())
		})

		It("should return 404 when file does not exist", func() {
			nonExistentFile := filepath.Join(tmpDir, "nonexistent.txt")

			req, _ := http.NewRequest("DELETE", "/files?path="+nonExistentFile, nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusNotFound))
		})
	})

	Context("delete directory", func() {
		It("should reject deleting directory without recursive flag", func() {
			testDir := filepath.Join(tmpDir, "testdir")
			err := os.Mkdir(testDir, 0o755)
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("DELETE", "/files?path="+testDir, nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
			Expect(w.Body.String()).To(ContainSubstring("recursive"))

			_, err = os.Stat(testDir)
			Expect(err).NotTo(HaveOccurred())
		})

		It("should delete directory recursively", func() {
			testDir := filepath.Join(tmpDir, "testdir")
			err := os.Mkdir(testDir, 0o755)
			Expect(err).NotTo(HaveOccurred())

			subDir := filepath.Join(testDir, "subdir")
			err = os.Mkdir(subDir, 0o755)
			Expect(err).NotTo(HaveOccurred())

			testFile := filepath.Join(subDir, "file.txt")
			err = os.WriteFile(testFile, []byte("content"), 0o644)
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("DELETE", "/files?path="+testDir+"&recursive=true", nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusNoContent))

			_, err = os.Stat(testDir)
			Expect(os.IsNotExist(err)).To(BeTrue())
		})

		It("should delete empty directory with recursive flag", func() {
			testDir := filepath.Join(tmpDir, "emptydir")
			err := os.Mkdir(testDir, 0o755)
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("DELETE", "/files?path="+testDir+"&recursive=true", nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusNoContent))

			_, err = os.Stat(testDir)
			Expect(os.IsNotExist(err)).To(BeTrue())
		})
	})

	Context("parameter validation", func() {
		It("should reject request without path parameter", func() {
			req, _ := http.NewRequest("DELETE", "/files", nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
			Expect(w.Body.String()).To(ContainSubstring("path is required"))
		})

		It("should reject empty path parameter", func() {
			req, _ := http.NewRequest("DELETE", "/files?path=", nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
			Expect(w.Body.String()).To(ContainSubstring("path is required"))
		})

		It("should handle recursive=false correctly", func() {
			testDir := filepath.Join(tmpDir, "testdir")
			err := os.Mkdir(testDir, 0o755)
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("DELETE", "/files?path="+testDir+"&recursive=false", nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))

			_, err = os.Stat(testDir)
			Expect(err).NotTo(HaveOccurred())
		})
	})
})
