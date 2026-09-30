package proxy

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"strings"
	"time"
)

// 上传会话 token 的签名域，避免密钥被挪作他用时产生可互换的签名
const sessionSigningDomain = "bkpaas-registry-proxy/upload-session/v1\n"

// uploadSession 是编码进客户端 Location 的上传会话状态，客户端每次续传时原样回传。
// 代理因此不保存任何会话状态，同一会话的请求可以落到任一副本。
type uploadSession struct {
	// Repo 为客户端视角的仓库路径，会话只能在该仓库下使用
	Repo string `json:"r"`
	// Location 为上游返回的续传地址（路径与查询串），相对于上游根地址
	Location string `json:"l"`
	// Expiry 为会话过期时刻（unix 秒），在会话开始时确定，续传时不延长
	Expiry int64 `json:"e"`
}

// sessionCodec 用 HMAC-SHA256 签名上传会话。Previous 为轮换前的密钥，只用于校验。
type sessionCodec struct {
	primary  []byte
	previous []byte
	ttl      time.Duration
	now      func() time.Time
}

var errInvalidSession = errors.New("invalid upload session")

// sign 签发会话 token；s.Expiry 为 0 时按 ttl 设置过期时刻
func (c *sessionCodec) sign(s uploadSession) (string, error) {
	if s.Expiry == 0 {
		s.Expiry = c.now().Add(c.ttl).Unix()
	}
	payload, err := json.Marshal(s)
	if err != nil {
		return "", err
	}
	p := base64.RawURLEncoding.EncodeToString(payload)
	return p + "." + base64.RawURLEncoding.EncodeToString(mac(c.primary, p)), nil
}

// verify 校验签名、过期时间，以及会话是否属于 repo
func (c *sessionCodec) verify(token, repo string) (uploadSession, error) {
	p, sig64, ok := strings.Cut(token, ".")
	if !ok {
		return uploadSession{}, errInvalidSession
	}
	sig, err := base64.RawURLEncoding.DecodeString(sig64)
	if err != nil {
		return uploadSession{}, errInvalidSession
	}
	if !hmac.Equal(sig, mac(c.primary, p)) && (len(c.previous) == 0 || !hmac.Equal(sig, mac(c.previous, p))) {
		return uploadSession{}, errInvalidSession
	}
	payload, err := base64.RawURLEncoding.DecodeString(p)
	if err != nil {
		return uploadSession{}, errInvalidSession
	}
	var s uploadSession
	if err := json.Unmarshal(payload, &s); err != nil || s.Repo == "" || s.Location == "" {
		return uploadSession{}, errInvalidSession
	}
	if s.Repo != repo || c.now().Unix() >= s.Expiry {
		return uploadSession{}, errInvalidSession
	}
	return s, nil
}

func mac(key []byte, payload string) []byte {
	h := hmac.New(sha256.New, key)
	h.Write([]byte(sessionSigningDomain))
	h.Write([]byte(payload))
	return h.Sum(nil)
}
