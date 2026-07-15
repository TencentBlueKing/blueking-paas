package pv

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"unicode/utf8"

	"github.com/gin-gonic/gin"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"golang.org/x/text/encoding/simplifiedchinese"
)

func doPreview(router *gin.Engine, req PreviewRequest) *httptest.ResponseRecorder {
	body, _ := json.Marshal(req)
	w := httptest.NewRecorder()
	httpReq, _ := http.NewRequest(http.MethodPost, "/files/cfs/preview", bytes.NewReader(body))
	httpReq.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(w, httpReq)
	return w
}

var _ = Describe("PreviewFile", func() {
	var (
		router   *gin.Engine
		cfsRoot  string
		jailRoot string
	)

	BeforeEach(func() {
		cfsRoot, jailRoot = newTestEnv()
		router = newTestRouter()
		router.POST("/files/cfs/preview", PreviewFile)
	})

	AfterEach(func() {
		os.RemoveAll(cfsRoot) // nolint
	})

	It("returns full text content when under the limit", func() {
		Expect(os.WriteFile(filepath.Join(jailRoot, "a.txt"), []byte("hello world"), 0o644)).To(Succeed())

		w := doPreview(router, PreviewRequest{BasePath: testBasePath, RelPath: "a.txt"})
		Expect(w.Code).To(Equal(http.StatusOK))
		Expect(w.Body.String()).To(Equal("hello world"))
		Expect(w.Header().Get("X-Truncated")).To(Equal("false"))
	})

	It("truncates and flags X-Truncated when over max_bytes", func() {
		Expect(os.WriteFile(filepath.Join(jailRoot, "big.txt"), []byte("abcdefghij"), 0o644)).To(Succeed())

		w := doPreview(router, PreviewRequest{BasePath: testBasePath, RelPath: "big.txt", MaxBytes: 4})
		Expect(w.Code).To(Equal(http.StatusOK))
		Expect(w.Body.String()).To(Equal("abcd"))
		Expect(w.Header().Get("X-Truncated")).To(Equal("true"))
	})

	It("returns 415 for a non-text file", func() {
		// 完整 PNG 签名, 让魔数嗅探能可靠识别为二进制
		Expect(os.WriteFile(filepath.Join(jailRoot, "img.png"),
			[]byte{0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A}, 0o644)).To(Succeed())

		w := doPreview(router, PreviewRequest{BasePath: testBasePath, RelPath: "img.png"})
		Expect(w.Code).To(Equal(http.StatusUnsupportedMediaType))
	})

	It("decodes GBK content to UTF-8", func() {
		gbk, err := simplifiedchinese.GBK.NewEncoder().Bytes([]byte("中文内容"))
		Expect(err).NotTo(HaveOccurred())
		Expect(os.WriteFile(filepath.Join(jailRoot, "gbk.txt"), gbk, 0o644)).To(Succeed())

		w := doPreview(router, PreviewRequest{BasePath: testBasePath, RelPath: "gbk.txt"})
		Expect(w.Code).To(Equal(http.StatusOK))
		Expect(w.Body.String()).To(Equal("中文内容"))
	})

	It("truncates UTF-8 multi-byte content on a rune boundary", func() {
		// 中文内容: 每个汉字 3 字节, 共 12 字节。逐字节滑动 max_bytes,
		// 截断点会落在多字节字符中间, 此时必须裁到字符边界, 不得产生乱码。
		Expect(os.WriteFile(filepath.Join(jailRoot, "u.txt"), []byte("中文内容"), 0o644)).To(Succeed())

		// n: max_bytes -> 期望返回内容
		Expectations := []struct {
			n        int64
			expected string
		}{
			{1, ""}, {2, ""}, {3, "中"},
			{4, "中"}, {5, "中"}, {6, "中文"},
			{7, "中文"}, {8, "中文"}, {9, "中文内"},
		}
		for _, e := range Expectations {
			w := doPreview(router, PreviewRequest{BasePath: testBasePath, RelPath: "u.txt", MaxBytes: e.n})
			Expect(w.Code).To(Equal(http.StatusOK), "max_bytes=%d", e.n)
			Expect(utf8.ValidString(w.Body.String())).To(BeTrue(), "max_bytes=%d produced invalid UTF-8", e.n)
			Expect(w.Body.String()).To(Equal(e.expected), "max_bytes=%d", e.n)
			Expect(w.Header().Get("X-Truncated")).To(Equal("true"), "max_bytes=%d", e.n)
		}
	})

	It("caps GBK->UTF-8 expansion on a rune boundary", func() {
		// GBK 中文每字 2 字节, 解码为 UTF-8 后每字 3 字节, 会膨胀超过 max_bytes。
		gbk, err := simplifiedchinese.GBK.NewEncoder().Bytes([]byte("中文内容"))
		Expect(err).NotTo(HaveOccurred())
		Expect(os.WriteFile(filepath.Join(jailRoot, "gbk-big.txt"), gbk, 0o644)).To(Succeed())

		// max_bytes=4: GBK 前 4 字节 = "中文", 解码后 6 字节超过 4 -> 裁到 "中"。
		w := doPreview(router, PreviewRequest{BasePath: testBasePath, RelPath: "gbk-big.txt", MaxBytes: 4})
		Expect(w.Code).To(Equal(http.StatusOK))
		Expect(utf8.ValidString(w.Body.String())).To(BeTrue())
		Expect(w.Body.String()).To(Equal("中"))
		Expect(w.Header().Get("X-Truncated")).To(Equal("true"))
	})

	It("returns 404 for a missing file", func() {
		w := doPreview(router, PreviewRequest{BasePath: testBasePath, RelPath: "nope.txt"})
		Expect(w.Code).To(Equal(http.StatusNotFound))
	})

	It("rejects a jail escape with 403", func() {
		w := doPreview(router, PreviewRequest{BasePath: testBasePath, RelPath: "../../etc/passwd"})
		Expect(w.Code).To(Equal(http.StatusForbidden))
	})
})
