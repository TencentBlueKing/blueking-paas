package pv

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"

	"github.com/gin-gonic/gin"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

func doDelete(router *gin.Engine, basePath, relPath string) *httptest.ResponseRecorder {
	q := url.Values{}
	q.Set("base_path", basePath)
	q.Set("rel_path", relPath)
	w := httptest.NewRecorder()
	httpReq, _ := http.NewRequest(http.MethodDelete, "/files?"+q.Encode(), nil)
	router.ServeHTTP(w, httpReq)
	return w
}

var _ = Describe("DeleteFile", func() {
	var (
		router   *gin.Engine
		rootDir  string
		jailRoot string
	)

	BeforeEach(func() {
		rootDir, jailRoot = newTestEnv()
		router = newTestRouter()
		router.DELETE("/files", DeleteFile)
	})

	AfterEach(func() {
		os.RemoveAll(rootDir) // nolint
	})

	It("deletes an existing file", func() {
		target := filepath.Join(jailRoot, "out.txt")
		Expect(os.WriteFile(target, []byte("x"), 0o644)).To(Succeed())

		w := doDelete(router, testBasePath, "out.txt")
		Expect(w.Code).To(Equal(http.StatusOK))

		var resp DeleteResponse
		Expect(json.Unmarshal(w.Body.Bytes(), &resp)).To(Succeed())
		Expect(resp.Deleted).To(BeTrue())

		_, err := os.Stat(target)
		Expect(os.IsNotExist(err)).To(BeTrue())
	})

	It("is idempotent for a missing file", func() {
		w := doDelete(router, testBasePath, "nope.txt")
		Expect(w.Code).To(Equal(http.StatusOK))

		var resp DeleteResponse
		Expect(json.Unmarshal(w.Body.Bytes(), &resp)).To(Succeed())
		Expect(resp.Deleted).To(BeTrue())
	})

	It("refuses to delete a directory", func() {
		Expect(os.MkdirAll(filepath.Join(jailRoot, "adir"), 0o755)).To(Succeed())

		w := doDelete(router, testBasePath, "adir")
		Expect(w.Code).To(Equal(http.StatusBadRequest))
	})

	It("rejects a jail escape with 403", func() {
		w := doDelete(router, testBasePath, "../../etc/passwd")
		Expect(w.Code).To(Equal(http.StatusForbidden))
	})

	It("removes a symlink without removing its target", func() {
		target := filepath.Join(jailRoot, "target.txt")
		link := filepath.Join(jailRoot, "link.txt")
		Expect(os.WriteFile(target, []byte("x"), 0o644)).To(Succeed())
		Expect(os.Symlink(target, link)).To(Succeed())

		w := doDelete(router, testBasePath, "link.txt")
		Expect(w.Code).To(Equal(http.StatusOK))
		_, err := os.Lstat(link)
		Expect(os.IsNotExist(err)).To(BeTrue())
		_, err = os.Stat(target)
		Expect(err).NotTo(HaveOccurred())
	})

	It("refuses to delete through a parent symlink that points outside the jail", func() {
		outside := filepath.Join(rootDir, "outside")
		Expect(os.MkdirAll(outside, 0o755)).To(Succeed())
		secret := filepath.Join(outside, "secret.txt")
		Expect(os.WriteFile(secret, []byte("secret"), 0o644)).To(Succeed())
		Expect(os.Symlink(outside, filepath.Join(jailRoot, "escape"))).To(Succeed())

		w := doDelete(router, testBasePath, "escape/secret.txt")
		Expect(w.Code).To(Equal(http.StatusForbidden))
		_, err := os.Stat(secret)
		Expect(err).NotTo(HaveOccurred())
	})

	It("rejects a missing base_path with 400", func() {
		w := doDelete(router, "", "x")
		Expect(w.Code).To(Equal(http.StatusBadRequest))
	})
})
