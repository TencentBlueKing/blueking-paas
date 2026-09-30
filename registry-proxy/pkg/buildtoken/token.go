// Package buildtoken 校验 apiserver 签发的构建 token，移植自参考实现 reference/token.go。
package buildtoken

import (
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"time"

	"github.com/golang-jwt/jwt/v5"

	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/oci"
)

const (
	Issuer        = "bkpaas-apiserver"
	ClaimsVersion = 1
	ClockLeeway   = 30 * time.Second
)

// Claims 是构建 token 的声明。仓库路径均为客户端视角：<上游别名>/<上游仓库路径>。
type Claims struct {
	jwt.RegisteredClaims
	Ver      int         `json:"ver"`
	AppCode  string      `json:"app_code"`
	Module   string      `json:"module"`
	Push     []PushGrant `json:"push"`
	Pull     []string    `json:"pull"`
	PullDeny []string    `json:"pull_deny"`
}

// PushGrant 限定可推送的仓库（精确匹配）与 tag，tags 含 "*" 表示任意引用
type PushGrant struct {
	Repo string   `json:"repo"`
	Tags []string `json:"tags"`
}

// Validate 在 golang-jwt 完成签名、iss、aud、exp、iat 校验后执行
func (c *Claims) Validate() error {
	if c.Ver != ClaimsVersion {
		return fmt.Errorf("unsupported claims version %d", c.Ver)
	}
	if c.Subject == "" || c.ID == "" {
		return errors.New("sub and jti are required")
	}
	for _, g := range c.Push {
		if g.Repo == "" || len(g.Tags) == 0 {
			return fmt.Errorf("invalid push grant %+v", g)
		}
	}
	return nil
}

// JWKThumbprint 按 RFC 7638 计算 Ed25519 公钥的 kid
func JWKThumbprint(x string) string {
	sum := sha256.Sum256([]byte(`{"crv":"Ed25519","kty":"OKP","x":"` + x + `"}`))
	return base64.RawURLEncoding.EncodeToString(sum[:])
}

type jwk struct {
	Kty string `json:"kty"`
	Crv string `json:"crv"`
	X   string `json:"x"`
	Kid string `json:"kid"`
	Alg string `json:"alg"`
	Use string `json:"use"`
	D   string `json:"d"`
}

// KeySet 是 kid → 公钥
type KeySet map[string]ed25519.PublicKey

// LoadJWKSFile 读取并解析公钥集合文件
func LoadJWKSFile(path string) (KeySet, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read jwks: %w", err)
	}
	return LoadJWKS(raw)
}

// LoadJWKS 解析公钥集合，拒绝含私钥、非 Ed25519 或 kid 与指纹不符的条目
func LoadJWKS(raw []byte) (KeySet, error) {
	var set struct {
		Keys []jwk `json:"keys"`
	}
	if err := json.Unmarshal(raw, &set); err != nil {
		return nil, errors.New("parse jwks: invalid JSON")
	}
	keys := KeySet{}
	for _, k := range set.Keys {
		switch {
		case k.D != "":
			return nil, fmt.Errorf("jwk %s contains private key", k.Kid)
		case k.Kty != "OKP" || k.Crv != "Ed25519" || k.Alg != "EdDSA" || k.Use != "sig":
			return nil, fmt.Errorf("jwk %s: want kty=OKP crv=Ed25519 alg=EdDSA use=sig", k.Kid)
		case k.Kid != JWKThumbprint(k.X):
			return nil, fmt.Errorf("jwk %s: kid is not the RFC 7638 thumbprint", k.Kid)
		}
		pub, err := base64.RawURLEncoding.DecodeString(k.X)
		if err != nil || len(pub) != ed25519.PublicKeySize {
			return nil, fmt.Errorf("jwk %s: invalid x", k.Kid)
		}
		keys[k.Kid] = ed25519.PublicKey(pub)
	}
	if len(keys) == 0 {
		return nil, errors.New("empty jwks")
	}
	return keys, nil
}

// Verify 校验构建 token，失败时返回的 deny 为 token_missing / token_expired / token_invalid
func Verify(raw string, keys KeySet, audience string, now time.Time) (*Claims, string, error) {
	if raw == "" {
		return nil, oci.DenyTokenMissing, errors.New("missing token")
	}
	c := &Claims{}
	_, err := jwt.ParseWithClaims(raw, c,
		func(t *jwt.Token) (any, error) {
			kid, _ := t.Header["kid"].(string)
			if k, ok := keys[kid]; ok {
				return k, nil
			}
			return nil, fmt.Errorf("unknown kid %q", kid)
		},
		jwt.WithValidMethods([]string{jwt.SigningMethodEdDSA.Alg()}),
		jwt.WithIssuer(Issuer),
		jwt.WithAudience(audience),
		jwt.WithExpirationRequired(),
		jwt.WithIssuedAt(),
		jwt.WithLeeway(ClockLeeway),
		jwt.WithTimeFunc(func() time.Time { return now }),
	)
	switch {
	case err == nil:
		return c, "", nil
	case errors.Is(err, jwt.ErrTokenExpired):
		return nil, oci.DenyTokenExpired, err
	default:
		return nil, oci.DenyTokenInvalid, err
	}
}
