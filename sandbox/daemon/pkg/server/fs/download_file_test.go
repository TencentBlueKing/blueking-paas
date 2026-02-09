package fs

import (
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"

	"github.com/gin-gonic/gin"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/httputil"
)

var _ = Describe("DownloadFile", func() {
	var (
		router *gin.Engine
		w      *httptest.ResponseRecorder
		tmpDir string
		url    string
	)

	BeforeEach(func() {
		gin.SetMode(gin.TestMode)

		url = "/files/download"

		var err error
		tmpDir, err = os.MkdirTemp("", "download-test-*")
		Expect(err).NotTo(HaveOccurred())

		router = gin.New()
		router.Use(httputil.ErrorMiddleware())
		router.GET(url, DownloadFile)

		w = httptest.NewRecorder()
	})

	AfterEach(func() {
		if tmpDir != "" {
			os.RemoveAll(tmpDir) // nolint
		}
	})

	Context("download regular file", func() {
		It("should download existing file successfully", func() {
			testFile := filepath.Join(tmpDir, "test.txt")
			testContent := []byte("test content")
			err := os.WriteFile(testFile, testContent, 0o644)
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("GET", url+"?path="+testFile, nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))

			// Verify headers
			Expect(w.Header().Get("Content-Description")).To(Equal("File Transfer"))
			Expect(w.Header().Get("Content-Type")).To(Equal("application/octet-stream"))
			Expect(w.Header().Get("Content-Disposition")).To(ContainSubstring("attachment"))
			Expect(w.Header().Get("Content-Disposition")).To(ContainSubstring("test.txt"))
			Expect(w.Header().Get("Content-Transfer-Encoding")).To(Equal("binary"))
			Expect(w.Header().Get("Expires")).To(Equal("0"))
			Expect(w.Header().Get("Cache-Control")).To(Equal("must-revalidate"))
			Expect(w.Header().Get("Pragma")).To(Equal("public"))

			// Verify content
			body, err := io.ReadAll(w.Body)
			Expect(err).NotTo(HaveOccurred())
			Expect(body).To(Equal(testContent))
		})

		It("should download file with different content types", func() {
			testCases := []struct {
				filename string
				content  []byte
			}{
				{"text.txt", []byte("plain text content")},
				{"data.json", []byte(`{"key": "value"}`)},
				{"script.sh", []byte("#!/bin/bash\necho hello")},
				{"binary.bin", []byte{0x00, 0x01, 0x02, 0xFF}},
			}

			for _, tc := range testCases {
				testFile := filepath.Join(tmpDir, tc.filename)
				err := os.WriteFile(testFile, tc.content, 0o644)
				Expect(err).NotTo(HaveOccurred())

				req, _ := http.NewRequest("GET", url+"?path="+testFile, nil)
				w = httptest.NewRecorder()
				router.ServeHTTP(w, req)

				Expect(w.Code).To(Equal(http.StatusOK))
				Expect(w.Header().Get("Content-Type")).To(Equal("application/octet-stream"))

				body, err := io.ReadAll(w.Body)
				Expect(err).NotTo(HaveOccurred())
				Expect(body).To(Equal(tc.content))
			}
		})

		It("should download empty file", func() {
			testFile := filepath.Join(tmpDir, "empty.txt")
			err := os.WriteFile(testFile, []byte{}, 0o644)
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("GET", url+"?path="+testFile, nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))

			body, err := io.ReadAll(w.Body)
			Expect(err).NotTo(HaveOccurred())
			Expect(len(body)).To(Equal(0))
		})

		It("should download large file", func() {
			testFile := filepath.Join(tmpDir, "large.bin")
			// Create a 1MB file
			largeContent := make([]byte, 1024*1024)
			for i := range largeContent {
				largeContent[i] = byte(i % 256)
			}
			err := os.WriteFile(testFile, largeContent, 0o644)
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("GET", url+"?path="+testFile, nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))

			body, err := io.ReadAll(w.Body)
			Expect(err).NotTo(HaveOccurred())
			Expect(len(body)).To(Equal(len(largeContent)))
			Expect(body).To(Equal(largeContent))
		})

		It("should return 404 when file does not exist", func() {
			nonExistentFile := filepath.Join(tmpDir, "nonexistent.txt")

			req, _ := http.NewRequest("GET", url+"?path="+nonExistentFile, nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusNotFound))
		})
	})

	Context("path handling", func() {
		It("should handle absolute path", func() {
			testFile := filepath.Join(tmpDir, "test.txt")
			err := os.WriteFile(testFile, []byte("content"), 0o644)
			Expect(err).NotTo(HaveOccurred())

			absPath, err := filepath.Abs(testFile)
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("GET", url+"?path="+absPath, nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))
		})

		It("should handle relative path", func() {
			testFile := filepath.Join(tmpDir, "test.txt")
			err := os.WriteFile(testFile, []byte("content"), 0o644)
			Expect(err).NotTo(HaveOccurred())

			// Change to tmpDir and use relative path
			originalWd, err := os.Getwd()
			Expect(err).NotTo(HaveOccurred())
			defer os.Chdir(originalWd) // nolint

			err = os.Chdir(tmpDir)
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("GET", url+"?path=test.txt", nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))
		})

		It("should handle nested directory path", func() {
			nestedDir := filepath.Join(tmpDir, "level1", "level2", "level3")
			err := os.MkdirAll(nestedDir, 0o755)
			Expect(err).NotTo(HaveOccurred())

			testFile := filepath.Join(nestedDir, "nested.txt")
			err = os.WriteFile(testFile, []byte("nested content"), 0o644)
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("GET", url+"?path="+testFile, nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))

			body, err := io.ReadAll(w.Body)
			Expect(err).NotTo(HaveOccurred())
			Expect(body).To(Equal([]byte("nested content")))
		})
	})

	Context("directory handling", func() {
		It("should reject downloading directory", func() {
			testDir := filepath.Join(tmpDir, "testdir")
			err := os.Mkdir(testDir, 0o755)
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("GET", url+"?path="+testDir, nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
			Expect(w.Body.String()).To(ContainSubstring("path must be a file"))
		})

		It("should reject downloading empty directory", func() {
			testDir := filepath.Join(tmpDir, "emptydir")
			err := os.Mkdir(testDir, 0o755)
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("GET", url+"?path="+testDir, nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
			Expect(w.Body.String()).To(ContainSubstring("path must be a file"))
		})
	})

	Context("parameter validation", func() {
		It("should reject request without path parameter", func() {
			req, _ := http.NewRequest("GET", url, nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
			Expect(w.Body.String()).To(ContainSubstring("path is required"))
		})

		It("should reject empty path parameter", func() {
			req, _ := http.NewRequest("GET", url+"?path=", nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
			Expect(w.Body.String()).To(ContainSubstring("path is required"))
		})
	})

	Context("edge cases", func() {
		It("should handle file with special characters in name", func() {
			testFile := filepath.Join(tmpDir, "test file with spaces.txt")
			testContent := []byte("content with spaces")
			err := os.WriteFile(testFile, testContent, 0o644)
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("GET", url+"?path="+testFile, nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))
			Expect(w.Header().Get("Content-Disposition")).To(ContainSubstring("test file with spaces.txt"))

			body, err := io.ReadAll(w.Body)
			Expect(err).NotTo(HaveOccurred())
			Expect(body).To(Equal(testContent))
		})

		It("should handle file with unicode characters in name", func() {
			testFile := filepath.Join(tmpDir, "测试文件.txt")
			testContent := []byte("中文内容")
			err := os.WriteFile(testFile, testContent, 0o644)
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("GET", url+"?path="+testFile, nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))
			Expect(w.Header().Get("Content-Disposition")).To(ContainSubstring("测试文件.txt"))

			body, err := io.ReadAll(w.Body)
			Expect(err).NotTo(HaveOccurred())
			Expect(body).To(Equal(testContent))
		})

		It("should handle file with dots in name", func() {
			testFile := filepath.Join(tmpDir, "file.name.with.dots.txt")
			testContent := []byte("dotted content")
			err := os.WriteFile(testFile, testContent, 0o644)
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("GET", url+"?path="+testFile, nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))
			Expect(w.Header().Get("Content-Disposition")).To(ContainSubstring("file.name.with.dots.txt"))
		})

		It("should handle hidden file", func() {
			testFile := filepath.Join(tmpDir, ".hidden")
			testContent := []byte("hidden content")
			err := os.WriteFile(testFile, testContent, 0o644)
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("GET", url+"?path="+testFile, nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))
			Expect(w.Header().Get("Content-Disposition")).To(ContainSubstring(".hidden"))

			body, err := io.ReadAll(w.Body)
			Expect(err).NotTo(HaveOccurred())
			Expect(body).To(Equal(testContent))
		})

		It("should handle symlink to file", func() {
			targetFile := filepath.Join(tmpDir, "target.txt")
			testContent := []byte("target content")
			err := os.WriteFile(targetFile, testContent, 0o644)
			Expect(err).NotTo(HaveOccurred())

			symlinkFile := filepath.Join(tmpDir, "symlink.txt")
			err = os.Symlink(targetFile, symlinkFile)
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("GET", url+"?path="+symlinkFile, nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))

			body, err := io.ReadAll(w.Body)
			Expect(err).NotTo(HaveOccurred())
			Expect(body).To(Equal(testContent))
		})

		It("should reject symlink to directory", func() {
			targetDir := filepath.Join(tmpDir, "targetdir")
			err := os.Mkdir(targetDir, 0o755)
			Expect(err).NotTo(HaveOccurred())

			symlinkDir := filepath.Join(tmpDir, "symlinkdir")
			err = os.Symlink(targetDir, symlinkDir)
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("GET", url+"?path="+symlinkDir, nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
			Expect(w.Body.String()).To(ContainSubstring("path must be a file"))
		})

		It("should handle file with no extension", func() {
			testFile := filepath.Join(tmpDir, "README")
			testContent := []byte("readme content")
			err := os.WriteFile(testFile, testContent, 0o644)
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("GET", url+"?path="+testFile, nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))
			Expect(w.Header().Get("Content-Disposition")).To(ContainSubstring("README"))

			body, err := io.ReadAll(w.Body)
			Expect(err).NotTo(HaveOccurred())
			Expect(body).To(Equal(testContent))
		})

		It("should handle file with multiple extensions", func() {
			testFile := filepath.Join(tmpDir, "archive.tar.gz")
			testContent := []byte("compressed content")
			err := os.WriteFile(testFile, testContent, 0o644)
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("GET", url+"?path="+testFile, nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))
			Expect(w.Header().Get("Content-Disposition")).To(ContainSubstring("archive.tar.gz"))
		})
	})

	Context("response headers", func() {
		It("should set correct headers for all downloads", func() {
			testFile := filepath.Join(tmpDir, "test.txt")
			err := os.WriteFile(testFile, []byte("content"), 0o644)
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("GET", url+"?path="+testFile, nil)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))

			// Verify all required headers are present
			headers := map[string]string{
				"Content-Description":       "File Transfer",
				"Content-Type":              "application/octet-stream",
				"Content-Transfer-Encoding": "binary",
				"Expires":                   "0",
				"Cache-Control":             "must-revalidate",
				"Pragma":                    "public",
			}

			for key, expectedValue := range headers {
				Expect(w.Header().Get(key)).To(Equal(expectedValue), "Header %s should be %s", key, expectedValue)
			}

			// Content-Disposition should contain attachment and filename
			contentDisposition := w.Header().Get("Content-Disposition")
			Expect(contentDisposition).To(ContainSubstring("attachment"))
			Expect(contentDisposition).To(ContainSubstring("filename="))
		})

		It("should extract correct filename from path", func() {
			testCases := []struct {
				path             string
				expectedFilename string
			}{
				{filepath.Join(tmpDir, "simple.txt"), "simple.txt"},
				{filepath.Join(tmpDir, "path", "to", "file.txt"), "file.txt"},
				{filepath.Join(tmpDir, "file-with-dash.txt"), "file-with-dash.txt"},
				{filepath.Join(tmpDir, "file_with_underscore.txt"), "file_with_underscore.txt"},
			}

			for _, tc := range testCases {
				// Create directory structure if needed
				dir := filepath.Dir(tc.path)
				if dir != tmpDir {
					err := os.MkdirAll(dir, 0o755)
					Expect(err).NotTo(HaveOccurred())
				}

				err := os.WriteFile(tc.path, []byte("content"), 0o644)
				Expect(err).NotTo(HaveOccurred())

				req, _ := http.NewRequest("GET", url+"?path="+tc.path, nil)
				w = httptest.NewRecorder()
				router.ServeHTTP(w, req)

				Expect(w.Code).To(Equal(http.StatusOK))
				Expect(w.Header().Get("Content-Disposition")).To(ContainSubstring(tc.expectedFilename))
			}
		})
	})
})
