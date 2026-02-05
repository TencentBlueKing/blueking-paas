package fs

import (
	"bytes"
	"io"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"

	"github.com/gin-gonic/gin"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/bkpaas/sandbox/daemon/pkg/server/httputil"
)

var _ = Describe("UploadFile", func() {
	var (
		router *gin.Engine
		w      *httptest.ResponseRecorder
		tmpDir string

		url string
	)

	BeforeEach(func() {
		gin.SetMode(gin.TestMode)

		url = "/files/upload"

		var err error
		tmpDir, err = os.MkdirTemp("", "upload-test-*")
		Expect(err).NotTo(HaveOccurred())

		router = gin.New()
		router.Use(httputil.ErrorMiddleware())
		router.POST(url, UploadFile)

		w = httptest.NewRecorder()
	})

	AfterEach(func() {
		if tmpDir != "" {
			os.RemoveAll(tmpDir) // nolint
		}
	})

	createMultipartRequest := func(destPath, filename, content string) *http.Request {
		body := &bytes.Buffer{}
		writer := multipart.NewWriter(body)

		err := writer.WriteField("destPath", destPath)
		Expect(err).NotTo(HaveOccurred())

		if filename != "" {
			part, err := writer.CreateFormFile("file", filename)
			Expect(err).NotTo(HaveOccurred())
			_, err = io.WriteString(part, content)
			Expect(err).NotTo(HaveOccurred())
		}

		err = writer.Close()
		Expect(err).NotTo(HaveOccurred())

		req, _ := http.NewRequest("POST", url, body)
		req.Header.Set("Content-Type", writer.FormDataContentType())
		return req
	}

	Context("upload file", func() {
		It("should upload file successfully", func() {
			destPath := filepath.Join(tmpDir, "uploaded.txt")
			content := "test file content"

			req := createMultipartRequest(destPath, "test.txt", content)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))

			data, err := os.ReadFile(destPath)
			Expect(err).NotTo(HaveOccurred())
			Expect(string(data)).To(Equal(content))
		})

		It("should upload binary file", func() {
			destPath := filepath.Join(tmpDir, "binary.bin")
			binaryContent := string([]byte{0x00, 0x01, 0x02, 0xFF, 0xFE})

			req := createMultipartRequest(destPath, "binary.bin", binaryContent)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))

			data, err := os.ReadFile(destPath)
			Expect(err).NotTo(HaveOccurred())
			Expect(data).To(Equal([]byte{0x00, 0x01, 0x02, 0xFF, 0xFE}))
		})

		It("should overwrite existing file", func() {
			destPath := filepath.Join(tmpDir, "existing.txt")

			err := os.WriteFile(destPath, []byte("old content"), 0o644)
			Expect(err).NotTo(HaveOccurred())

			newContent := "new content"
			req := createMultipartRequest(destPath, "new.txt", newContent)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))

			data, err := os.ReadFile(destPath)
			Expect(err).NotTo(HaveOccurred())
			Expect(string(data)).To(Equal(newContent))
		})

		It("should upload to existing directory", func() {
			subDir := filepath.Join(tmpDir, "subdir")
			err := os.Mkdir(subDir, 0o755)
			Expect(err).NotTo(HaveOccurred())

			destPath := filepath.Join(subDir, "file.txt")
			content := "content in subdir"

			req := createMultipartRequest(destPath, "file.txt", content)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))

			data, err := os.ReadFile(destPath)
			Expect(err).NotTo(HaveOccurred())
			Expect(string(data)).To(Equal(content))
		})
	})

	Context("parameter validation", func() {
		It("should reject request without destPath parameter", func() {
			body := &bytes.Buffer{}
			writer := multipart.NewWriter(body)

			part, err := writer.CreateFormFile("file", "test.txt")
			Expect(err).NotTo(HaveOccurred())
			_, err = io.WriteString(part, "content")
			Expect(err).NotTo(HaveOccurred())

			err = writer.Close()
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("POST", url, body)
			req.Header.Set("Content-Type", writer.FormDataContentType())

			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
			Expect(w.Body.String()).To(ContainSubstring("destPath is required"))
		})

		It("should reject empty destPath parameter", func() {
			body := &bytes.Buffer{}
			writer := multipart.NewWriter(body)

			err := writer.WriteField("destPath", "")
			Expect(err).NotTo(HaveOccurred())

			part, err := writer.CreateFormFile("file", "test.txt")
			Expect(err).NotTo(HaveOccurred())
			_, err = io.WriteString(part, "content")
			Expect(err).NotTo(HaveOccurred())

			err = writer.Close()
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("POST", url, body)
			req.Header.Set("Content-Type", writer.FormDataContentType())

			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
			Expect(w.Body.String()).To(ContainSubstring("destPath is required"))
		})

		It("should reject request without file", func() {
			destPath := filepath.Join(tmpDir, "file.txt")

			body := &bytes.Buffer{}
			writer := multipart.NewWriter(body)

			err := writer.WriteField("destPath", destPath)
			Expect(err).NotTo(HaveOccurred())

			err = writer.Close()
			Expect(err).NotTo(HaveOccurred())

			req, _ := http.NewRequest("POST", url, body)
			req.Header.Set("Content-Type", writer.FormDataContentType())

			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
		})

		It("should reject non-multipart request", func() {
			req, _ := http.NewRequest("POST", url, bytes.NewBufferString("not multipart"))
			req.Header.Set("Content-Type", "application/json")

			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
		})
	})

	Context("error handling", func() {
		It("should handle invalid destination path", func() {
			invalidPath := string([]byte{0x00})

			req := createMultipartRequest(invalidPath, "test.txt", "content")
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusBadRequest))
		})
	})

	Context("filename handling", func() {
		It("should use destPath instead of original filename", func() {
			destPath := filepath.Join(tmpDir, "custom-name.txt")
			content := "test content"

			req := createMultipartRequest(destPath, "original.txt", content)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))

			data, err := os.ReadFile(destPath)
			Expect(err).NotTo(HaveOccurred())
			Expect(string(data)).To(Equal(content))

			_, err = os.Stat(filepath.Join(tmpDir, "original.txt"))
			Expect(os.IsNotExist(err)).To(BeTrue())
		})

		It("should handle special characters in filename", func() {
			destPath := filepath.Join(tmpDir, "文件-with-特殊字符.txt")
			content := "special chars content"

			req := createMultipartRequest(destPath, "test.txt", content)
			router.ServeHTTP(w, req)

			Expect(w.Code).To(Equal(http.StatusOK))

			data, err := os.ReadFile(destPath)
			Expect(err).NotTo(HaveOccurred())
			Expect(string(data)).To(Equal(content))
		})
	})
})
