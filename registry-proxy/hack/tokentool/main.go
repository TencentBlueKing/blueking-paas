// tokentool 是测试脚本使用的构建 token 工具，行为与签发端样例 build_token.py 一致：
//
//	tokentool keygen -out key.pem
//	tokentool jwks -out jwks.json key.pem [key2.pem ...]
//	tokentool sign -key key.pem -claims claims.json -audience bkpaas-registry-proxy:<集群名> [-timeout 900] [-expired]
//
// claims.json 只需包含 sub、app_code、module、push、pull、pull_deny，其余声明由工具补全。
// 私钥与 token 只写入文件或 stdout。
package main

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/x509"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"encoding/pem"
	"errors"
	"flag"
	"fmt"
	"os"
	"time"

	"github.com/golang-jwt/jwt/v5"

	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/buildtoken"
)

// exp = iat + BUILD_PROCESS_TIMEOUT + tokenGrace
const tokenGrace = 300 * time.Second

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: tokentool keygen|jwks|sign ...")
		os.Exit(2)
	}
	var err error
	switch os.Args[1] {
	case "keygen":
		err = keygen(os.Args[2:])
	case "jwks":
		err = exportJWKS(os.Args[2:])
	case "sign":
		err = sign(os.Args[2:])
	default:
		err = fmt.Errorf("unknown command %q", os.Args[1])
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func keygen(args []string) error {
	fs := flag.NewFlagSet("keygen", flag.ExitOnError)
	out := fs.String("out", "", "私钥输出文件")
	_ = fs.Parse(args)
	_, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		return err
	}
	der, err := x509.MarshalPKCS8PrivateKey(priv)
	if err != nil {
		return err
	}
	return os.WriteFile(*out, pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: der}), 0o600)
}

func loadKey(path string) (ed25519.PrivateKey, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	block, _ := pem.Decode(raw)
	if block == nil {
		return nil, errors.New("invalid PEM")
	}
	key, err := x509.ParsePKCS8PrivateKey(block.Bytes)
	if err != nil {
		return nil, err
	}
	priv, ok := key.(ed25519.PrivateKey)
	if !ok {
		return nil, errors.New("not an Ed25519 private key")
	}
	return priv, nil
}

func publicJWK(priv ed25519.PrivateKey) map[string]string {
	x := base64.RawURLEncoding.EncodeToString(priv.Public().(ed25519.PublicKey))
	return map[string]string{"kty": "OKP", "crv": "Ed25519", "x": x, "kid": buildtoken.JWKThumbprint(x), "alg": "EdDSA", "use": "sig"}
}

func exportJWKS(args []string) error {
	fs := flag.NewFlagSet("jwks", flag.ExitOnError)
	out := fs.String("out", "", "JWKS 输出文件")
	_ = fs.Parse(args)
	var keys []map[string]string
	for _, p := range fs.Args() {
		priv, err := loadKey(p)
		if err != nil {
			return fmt.Errorf("%s: %w", p, err)
		}
		keys = append(keys, publicJWK(priv))
	}
	raw, _ := json.MarshalIndent(map[string]any{"keys": keys}, "", "  ")
	return os.WriteFile(*out, raw, 0o644)
}

func sign(args []string) error {
	fs := flag.NewFlagSet("sign", flag.ExitOnError)
	keyFile := fs.String("key", "", "签名私钥")
	claimsFile := fs.String("claims", "", "声明模板（sub/app_code/module/push/pull/pull_deny）")
	audience := fs.String("audience", "", "bkpaas-registry-proxy:<集群名>")
	timeout := fs.Duration("timeout", 900*time.Second, "BUILD_PROCESS_TIMEOUT")
	expired := fs.Bool("expired", false, "签发一个已过期的 token，用于负面用例")
	_ = fs.Parse(args)

	priv, err := loadKey(*keyFile)
	if err != nil {
		return err
	}
	raw, err := os.ReadFile(*claimsFile)
	if err != nil {
		return err
	}
	claims := jwt.MapClaims{}
	if err := json.Unmarshal(raw, &claims); err != nil {
		return err
	}
	now := time.Now()
	if *expired {
		now = now.Add(-(*timeout + tokenGrace + time.Hour))
	}
	jti := make([]byte, 16)
	_, _ = rand.Read(jti)
	claims["iss"] = buildtoken.Issuer
	claims["aud"] = *audience
	claims["jti"] = hex.EncodeToString(jti)
	claims["iat"] = now.Unix()
	claims["exp"] = now.Add(*timeout + tokenGrace).Unix()
	claims["ver"] = buildtoken.ClaimsVersion

	tok := jwt.NewWithClaims(jwt.SigningMethodEdDSA, claims)
	tok.Header["kid"] = publicJWK(priv)["kid"]
	s, err := tok.SignedString(priv)
	if err != nil {
		return err
	}
	fmt.Println(s)
	return nil
}
