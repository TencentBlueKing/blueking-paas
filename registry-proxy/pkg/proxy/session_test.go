package proxy

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"strings"
	"time"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

func newCodec(now *time.Time, primary, previous string) *sessionCodec {
	return &sessionCodec{
		primary:  []byte(primary),
		previous: []byte(previous),
		ttl:      time.Hour,
		now:      func() time.Time { return *now },
	}
}

var _ = Describe("sessionCodec", func() {
	var (
		now time.Time
		c   *sessionCodec
	)

	BeforeEach(func() {
		now = time.Now()
		c = newCodec(&now, strings.Repeat("a", 32), "")
	})

	It("round-trips a path-safe token and keeps the original expiry on resume", func() {
		tok, err := c.sign(uploadSession{Repo: "alias/app", Location: "/v2/app/blobs/uploads/u1?_state=x"})
		Expect(err).NotTo(HaveOccurred())
		Expect(strings.ContainsAny(tok, "/?&=%")).To(BeFalse(), "token %q is not path safe", tok)

		s, err := c.verify(tok, "alias/app")
		Expect(err).NotTo(HaveOccurred())
		Expect(s.Location).To(Equal("/v2/app/blobs/uploads/u1?_state=x"))
		Expect(s.Expiry).To(Equal(now.Add(time.Hour).Unix()))

		now = now.Add(30 * time.Minute)
		tok2, _ := c.sign(uploadSession{Repo: s.Repo, Location: "/v2/app/blobs/uploads/u1?_state=y", Expiry: s.Expiry})
		s2, err := c.verify(tok2, "alias/app")
		Expect(err).NotTo(HaveOccurred())
		Expect(s2.Expiry).To(Equal(s.Expiry), "expiry must not be extended")
	})

	DescribeTable("rejects",
		func(token func(tok string) string, repo string) {
			tok, _ := c.sign(uploadSession{Repo: "alias/app", Location: "/v2/app/blobs/uploads/u1"})
			_, err := c.verify(token(tok), repo)
			Expect(err).To(HaveOccurred())
		},
		Entry("other repo", func(tok string) string { return tok }, "alias/app/cache"),
		Entry("other key", func(string) string {
			now := time.Now()
			forged, _ := newCodec(&now, strings.Repeat("b", 32), "").sign(
				uploadSession{Repo: "alias/app", Location: "/v2/app/blobs/uploads/u1"})
			return forged
		}, "alias/app"),
		Entry("tampered payload", func(tok string) string {
			payload, sig, _ := strings.Cut(tok, ".")
			return payload + "x." + sig
		}, "alias/app"),
		Entry("no signature", func(tok string) string {
			payload, _, _ := strings.Cut(tok, ".")
			return payload
		}, "alias/app"),
		Entry("empty", func(string) string { return "" }, "alias/app"),
		Entry("garbage", func(string) string { return "forged.session" }, "alias/app"),
		Entry("bad base64 signature", func(tok string) string {
			payload, _, _ := strings.Cut(tok, ".")
			return payload + ".!!"
		}, "alias/app"),
	)

	It("rejects an expired session", func() {
		tok, _ := c.sign(uploadSession{Repo: "alias/app", Location: "/v2/app/blobs/uploads/u1"})
		now = now.Add(time.Hour)
		_, err := c.verify(tok, "alias/app")
		Expect(err).To(HaveOccurred())
	})

	It("verifies sessions signed by the previous key during rotation", func() {
		oldKey, newKey := strings.Repeat("o", 32), strings.Repeat("n", 32)
		tok, _ := newCodec(&now, oldKey, "").sign(uploadSession{Repo: "a/b", Location: "/v2/b/blobs/uploads/u"})

		_, err := newCodec(&now, newKey, oldKey).verify(tok, "a/b")
		Expect(err).NotTo(HaveOccurred())
		_, err = newCodec(&now, newKey, "").verify(tok, "a/b")
		Expect(err).To(HaveOccurred(), "session signed by a retired key must be rejected")
	})

	// 同一把密钥对 payload 直接做的 HMAC（不带签名域）不能通过校验
	It("separates the signing domain", func() {
		key := bytes.Repeat([]byte("k"), 32)
		c = newCodec(&now, string(key), "")
		tok, _ := c.sign(uploadSession{Repo: "a/b", Location: "/l"})
		payload, _, _ := strings.Cut(tok, ".")

		h := hmac.New(sha256.New, key)
		h.Write([]byte(payload))
		_, err := c.verify(payload+"."+base64.RawURLEncoding.EncodeToString(h.Sum(nil)), "a/b")
		Expect(err).To(HaveOccurred())
	})
})
