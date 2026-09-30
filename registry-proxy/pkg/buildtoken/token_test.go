package buildtoken

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"strings"
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v5"

	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/oci"
)

const audience = "bkpaas-registry-proxy:default-main"

type testKey struct {
	priv ed25519.PrivateKey
	x    string
	kid  string
}

func newTestKey(t *testing.T) testKey {
	t.Helper()
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		t.Fatal(err)
	}
	x := base64.RawURLEncoding.EncodeToString(pub)
	return testKey{priv: priv, x: x, kid: JWKThumbprint(x)}
}

func (k testKey) jwk() map[string]string {
	return map[string]string{"kty": "OKP", "crv": "Ed25519", "x": k.x, "kid": k.kid, "alg": "EdDSA", "use": "sig"}
}

func jwks(t *testing.T, keys ...map[string]string) KeySet {
	t.Helper()
	raw, _ := json.Marshal(map[string]any{"keys": keys})
	set, err := LoadJWKS(raw)
	if err != nil {
		t.Fatal(err)
	}
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

func sign(t *testing.T, k testKey, claims jwt.MapClaims) string {
	t.Helper()
	tok := jwt.NewWithClaims(jwt.SigningMethodEdDSA, claims)
	tok.Header["kid"] = k.kid
	s, err := tok.SignedString(k.priv)
	if err != nil {
		t.Fatal(err)
	}
	return s
}

func TestVerifyValid(t *testing.T) {
	k := newTestKey(t)
	now := time.Now()
	c, deny, err := Verify(sign(t, k, validClaims(now)), jwks(t, k.jwk()), audience, now)
	if err != nil || deny != "" {
		t.Fatalf("deny=%q err=%v", deny, err)
	}
	if c.Subject == "" || c.AppCode != "demo" || len(c.Push) != 1 || c.PullDeny[0] != "mirrors-example-com/bkpaas/docker/" {
		t.Fatalf("claims = %+v", c)
	}
}

func TestVerifyRejects(t *testing.T) {
	k := newTestKey(t)
	rogue := newTestKey(t)
	keys := jwks(t, k.jwk())
	now := time.Now()

	mutate := func(f func(jwt.MapClaims)) string {
		c := validClaims(now)
		f(c)
		return sign(t, k, c)
	}
	hs256 := func() string {
		tok := jwt.NewWithClaims(jwt.SigningMethodHS256, validClaims(now))
		tok.Header["kid"] = k.kid
		s, _ := tok.SignedString([]byte(k.x))
		return s
	}
	cases := map[string]struct {
		token string
		deny  string
	}{
		"missing":       {"", oci.DenyTokenMissing},
		"rogue key":     {func() string { r := rogue; r.kid = k.kid; return sign(t, r, validClaims(now)) }(), oci.DenyTokenInvalid},
		"unknown kid":   {sign(t, rogue, validClaims(now)), oci.DenyTokenInvalid},
		"hs256":         {hs256(), oci.DenyTokenInvalid},
		"other cluster": {mutate(func(c jwt.MapClaims) { c["aud"] = "bkpaas-registry-proxy:other" }), oci.DenyTokenInvalid},
		"issuer":        {mutate(func(c jwt.MapClaims) { c["iss"] = "someone" }), oci.DenyTokenInvalid},
		"expired":       {mutate(func(c jwt.MapClaims) { c["exp"] = now.Add(-31 * time.Second).Unix() }), oci.DenyTokenExpired},
		"no exp":        {mutate(func(c jwt.MapClaims) { delete(c, "exp") }), oci.DenyTokenInvalid},
		"future iat":    {mutate(func(c jwt.MapClaims) { c["iat"] = now.Add(31 * time.Second).Unix() }), oci.DenyTokenInvalid},
		"version":       {mutate(func(c jwt.MapClaims) { c["ver"] = 2 }), oci.DenyTokenInvalid},
		"no jti":        {mutate(func(c jwt.MapClaims) { delete(c, "jti") }), oci.DenyTokenInvalid},
		"empty tags": {mutate(func(c jwt.MapClaims) {
			c["push"] = []map[string]any{{"repo": "a/b", "tags": []string{}}}
		}), oci.DenyTokenInvalid},
		"none": {func() string {
			s := sign(t, k, validClaims(now))
			parts := strings.Split(s, ".")
			h := base64.RawURLEncoding.EncodeToString([]byte(`{"alg":"none","kid":"` + k.kid + `"}`))
			return h + "." + parts[1] + "."
		}(), oci.DenyTokenInvalid},
	}
	for name, tc := range cases {
		t.Run(name, func(t *testing.T) {
			if _, deny, _ := Verify(tc.token, keys, audience, now); deny != tc.deny {
				t.Fatalf("deny = %q, want %q", deny, tc.deny)
			}
		})
	}
}

func TestClockLeeway(t *testing.T) {
	k := newTestKey(t)
	now := time.Now()
	c := validClaims(now)
	c["exp"] = now.Add(-29 * time.Second).Unix()
	c["iat"] = now.Add(29 * time.Second).Unix()
	if _, deny, err := Verify(sign(t, k, c), jwks(t, k.jwk()), audience, now); deny != "" {
		t.Fatalf("within leeway: deny=%q err=%v", deny, err)
	}
}

func TestKeyRotation(t *testing.T) {
	oldKey, newKey := newTestKey(t), newTestKey(t)
	keys := jwks(t, oldKey.jwk(), newKey.jwk())
	now := time.Now()
	for _, k := range []testKey{oldKey, newKey} {
		if _, deny, _ := Verify(sign(t, k, validClaims(now)), keys, audience, now); deny != "" {
			t.Fatalf("deny = %q", deny)
		}
	}
}

func TestLoadJWKSRejects(t *testing.T) {
	k := newTestKey(t)
	withD := k.jwk()
	withD["d"] = "private"
	badKid := k.jwk()
	badKid["kid"] = "not-a-thumbprint"
	wrongAlg := k.jwk()
	wrongAlg["alg"] = "ES256"
	for name, key := range map[string]map[string]string{"private member": withD, "kid": badKid, "alg": wrongAlg} {
		raw, _ := json.Marshal(map[string]any{"keys": []any{key}})
		if _, err := LoadJWKS(raw); err == nil {
			t.Errorf("%s: want error", name)
		}
	}
	if _, err := LoadJWKS([]byte(`{"keys": []}`)); err == nil {
		t.Error("empty jwks: want error")
	}
}
