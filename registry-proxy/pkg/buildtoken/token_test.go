package buildtoken

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"strings"
	"time"

	"github.com/golang-jwt/jwt/v5"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/oci"
)

const audience = "bkpaas-registry-proxy:default-main"

type testKey struct {
	priv ed25519.PrivateKey
	x    string
	kid  string
}

func newTestKey() testKey {
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	Expect(err).NotTo(HaveOccurred())
	x := base64.RawURLEncoding.EncodeToString(pub)
	return testKey{priv: priv, x: x, kid: JWKThumbprint(x)}
}

func (k testKey) jwk() map[string]string {
	return map[string]string{"kty": "OKP", "crv": "Ed25519", "x": k.x, "kid": k.kid, "alg": "EdDSA", "use": "sig"}
}

func jwks(keys ...map[string]string) KeySet {
	raw, _ := json.Marshal(map[string]any{"keys": keys})
	set, err := LoadJWKS(raw)
	Expect(err).NotTo(HaveOccurred())
	return set
}

func validClaims(now time.Time) jwt.MapClaims {
	return jwt.MapClaims{
		"iss": Issuer, "aud": audience, "sub": "4b3a1c1e-5a0f-4c8e-9b7d-2f6f0a1d9e3c",
		"jti": "5f0c2b7e9d4a4c1e8b3f6a2d1c0e9f87", "iat": now.Unix(), "exp": now.Add(20 * time.Minute).Unix(),
		"ver": 1, "app_code": "demo", "module": "default",
		"push":      []map[string]any{{"repo": "mirrors-example-com/bkpaas/docker/demo/default", "tags": []string{"v1"}}},
		"pull":      []string{"mirrors-example-com/"},
		"pull_deny": []string{"mirrors-example-com/bkpaas/docker/"},
	}
}

func sign(k testKey, claims jwt.MapClaims) string {
	tok := jwt.NewWithClaims(jwt.SigningMethodEdDSA, claims)
	tok.Header["kid"] = k.kid
	s, err := tok.SignedString(k.priv)
	Expect(err).NotTo(HaveOccurred())
	return s
}

var _ = Describe("Verify", func() {
	var (
		k    testKey
		keys KeySet
		now  time.Time
	)

	BeforeEach(func() {
		k = newTestKey()
		keys = jwks(k.jwk())
		now = time.Now()
	})

	It("accepts a valid token", func() {
		c, deny, err := Verify(sign(k, validClaims(now)), keys, audience, now)
		Expect(err).NotTo(HaveOccurred())
		Expect(deny).To(BeEmpty())
		Expect(c.Subject).NotTo(BeEmpty())
		Expect(c.AppCode).To(Equal("demo"))
		Expect(c.Push).To(HaveLen(1))
		Expect(c.PullDeny).To(Equal([]string{"mirrors-example-com/bkpaas/docker/"}))
	})

	It("tolerates clock skew within the leeway", func() {
		c := validClaims(now)
		c["exp"] = now.Add(-29 * time.Second).Unix()
		c["iat"] = now.Add(29 * time.Second).Unix()
		_, deny, err := Verify(sign(k, c), keys, audience, now)
		Expect(err).NotTo(HaveOccurred())
		Expect(deny).To(BeEmpty())
	})

	It("accepts tokens signed by any key in the jwks during rotation", func() {
		newKey := newTestKey()
		rotating := jwks(k.jwk(), newKey.jwk())
		for _, key := range []testKey{k, newKey} {
			_, deny, _ := Verify(sign(key, validClaims(now)), rotating, audience, now)
			Expect(deny).To(BeEmpty())
		}
	})

	DescribeTable("rejects",
		func(token func(k testKey, now time.Time) string, want string) {
			_, deny, _ := Verify(token(k, now), keys, audience, now)
			Expect(deny).To(Equal(want))
		},
		Entry("missing token", func(testKey, time.Time) string { return "" }, oci.DenyTokenMissing),
		Entry("rogue key with a known kid", func(k testKey, now time.Time) string {
			r := newTestKey()
			r.kid = k.kid
			return sign(r, validClaims(now))
		}, oci.DenyTokenInvalid),
		Entry("unknown kid", func(_ testKey, now time.Time) string {
			return sign(newTestKey(), validClaims(now))
		}, oci.DenyTokenInvalid),
		Entry("HS256 keyed with the public key", func(k testKey, now time.Time) string {
			tok := jwt.NewWithClaims(jwt.SigningMethodHS256, validClaims(now))
			tok.Header["kid"] = k.kid
			s, _ := tok.SignedString([]byte(k.x))
			return s
		}, oci.DenyTokenInvalid),
		Entry("alg none", func(k testKey, now time.Time) string {
			parts := strings.Split(sign(k, validClaims(now)), ".")
			h := base64.RawURLEncoding.EncodeToString([]byte(`{"alg":"none","kid":"` + k.kid + `"}`))
			return h + "." + parts[1] + "."
		}, oci.DenyTokenInvalid),
		Entry("other cluster", mutated(func(c jwt.MapClaims, _ time.Time) {
			c["aud"] = "bkpaas-registry-proxy:other"
		}), oci.DenyTokenInvalid),
		Entry("issuer", mutated(func(c jwt.MapClaims, _ time.Time) { c["iss"] = "someone" }), oci.DenyTokenInvalid),
		Entry("expired", mutated(func(c jwt.MapClaims, now time.Time) {
			c["exp"] = now.Add(-31 * time.Second).Unix()
		}), oci.DenyTokenExpired),
		Entry("no exp", mutated(func(c jwt.MapClaims, _ time.Time) { delete(c, "exp") }), oci.DenyTokenInvalid),
		Entry("future iat", mutated(func(c jwt.MapClaims, now time.Time) {
			c["iat"] = now.Add(31 * time.Second).Unix()
		}), oci.DenyTokenInvalid),
		Entry("unsupported version", mutated(func(c jwt.MapClaims, _ time.Time) { c["ver"] = 2 }), oci.DenyTokenInvalid),
		Entry("no jti", mutated(func(c jwt.MapClaims, _ time.Time) { delete(c, "jti") }), oci.DenyTokenInvalid),
		Entry("push grant without tags", mutated(func(c jwt.MapClaims, _ time.Time) {
			c["push"] = []map[string]any{{"repo": "a/b", "tags": []string{}}}
		}), oci.DenyTokenInvalid),
	)
})

// mutated 用 k 签发一个经 f 修改过的合法声明
func mutated(f func(c jwt.MapClaims, now time.Time)) func(k testKey, now time.Time) string {
	return func(k testKey, now time.Time) string {
		c := validClaims(now)
		f(c, now)
		return sign(k, c)
	}
}

var _ = Describe("LoadJWKS", func() {
	var k testKey

	BeforeEach(func() { k = newTestKey() })

	DescribeTable("rejects invalid keys",
		func(mutate func(map[string]string)) {
			key := k.jwk()
			mutate(key)
			raw, _ := json.Marshal(map[string]any{"keys": []any{key}})
			_, err := LoadJWKS(raw)
			Expect(err).To(HaveOccurred())
		},
		Entry("private member", func(key map[string]string) { key["d"] = "private" }),
		Entry("kid is not the thumbprint", func(key map[string]string) { key["kid"] = "not-a-thumbprint" }),
		Entry("wrong alg", func(key map[string]string) { key["alg"] = "ES256" }),
	)

	It("rejects an empty jwks", func() {
		_, err := LoadJWKS([]byte(`{"keys": []}`))
		Expect(err).To(HaveOccurred())
	})
})
