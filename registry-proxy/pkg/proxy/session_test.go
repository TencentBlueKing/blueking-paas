package proxy

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"strings"
	"testing"
	"time"
)

func newCodec(now *time.Time, primary, previous string) *sessionCodec {
	return &sessionCodec{
		primary:  []byte(primary),
		previous: []byte(previous),
		ttl:      time.Hour,
		now:      func() time.Time { return *now },
	}
}

func TestSessionRoundTrip(t *testing.T) {
	now := time.Now()
	c := newCodec(&now, strings.Repeat("a", 32), "")
	tok, err := c.sign(uploadSession{Repo: "alias/app", Location: "/v2/app/blobs/uploads/u1?_state=x"})
	if err != nil {
		t.Fatal(err)
	}
	if strings.ContainsAny(tok, "/?&=%") {
		t.Fatalf("token %q is not path safe", tok)
	}
	s, err := c.verify(tok, "alias/app")
	if err != nil || s.Location != "/v2/app/blobs/uploads/u1?_state=x" || s.Expiry != now.Add(time.Hour).Unix() {
		t.Fatalf("verify = %+v, %v", s, err)
	}
	// 续传时保留原过期时刻
	now = now.Add(30 * time.Minute)
	tok2, _ := c.sign(uploadSession{Repo: s.Repo, Location: "/v2/app/blobs/uploads/u1?_state=y", Expiry: s.Expiry})
	if s2, _ := c.verify(tok2, "alias/app"); s2.Expiry != s.Expiry {
		t.Fatalf("expiry extended: %d != %d", s2.Expiry, s.Expiry)
	}
}

func TestSessionRejects(t *testing.T) {
	now := time.Now()
	c := newCodec(&now, strings.Repeat("a", 32), "")
	tok, _ := c.sign(uploadSession{Repo: "alias/app", Location: "/v2/app/blobs/uploads/u1"})
	payload, sig, _ := strings.Cut(tok, ".")

	other := newCodec(&now, strings.Repeat("b", 32), "")
	forged, _ := other.sign(uploadSession{Repo: "alias/app", Location: "/v2/app/blobs/uploads/u1"})

	cases := map[string]struct{ token, repo string }{
		"other repo":     {tok, "alias/app/cache"},
		"other key":      {forged, "alias/app"},
		"tampered":       {payload + "x." + sig, "alias/app"},
		"no signature":   {payload, "alias/app"},
		"empty":          {"", "alias/app"},
		"garbage":        {"forged.session", "alias/app"},
		"bad base64 sig": {payload + ".!!", "alias/app"},
	}
	for name, tc := range cases {
		if _, err := c.verify(tc.token, tc.repo); err == nil {
			t.Errorf("%s: want error", name)
		}
	}
	now = now.Add(time.Hour)
	if _, err := c.verify(tok, "alias/app"); err == nil {
		t.Error("expired session: want error")
	}
}

func TestSessionKeyRotation(t *testing.T) {
	now := time.Now()
	oldKey, newKey := strings.Repeat("o", 32), strings.Repeat("n", 32)
	tok, _ := newCodec(&now, oldKey, "").sign(uploadSession{Repo: "a/b", Location: "/v2/b/blobs/uploads/u"})

	if _, err := newCodec(&now, newKey, oldKey).verify(tok, "a/b"); err != nil {
		t.Fatalf("previous key must still verify: %v", err)
	}
	if _, err := newCodec(&now, newKey, "").verify(tok, "a/b"); err == nil {
		t.Fatal("session signed by a retired key must be rejected")
	}
}

// 同一把密钥对 payload 直接做的 HMAC（不带签名域）不能通过校验
func TestSessionSignatureIsDomainSeparated(t *testing.T) {
	key := bytes.Repeat([]byte("k"), 32)
	now := time.Now()
	c := newCodec(&now, string(key), "")
	tok, _ := c.sign(uploadSession{Repo: "a/b", Location: "/l"})
	payload, _, _ := strings.Cut(tok, ".")

	h := hmac.New(sha256.New, key)
	h.Write([]byte(payload))
	if _, err := c.verify(payload+"."+base64.RawURLEncoding.EncodeToString(h.Sum(nil)), "a/b"); err == nil {
		t.Fatal("signature without domain separation must be rejected")
	}
}
