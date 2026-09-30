package upstream

import (
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"net/url"
	"os"
	"strings"
)

// Credential 是代理访问某个上游使用的凭证，只存在于代理进程内
type Credential struct {
	Username string
	Password string
	// RegistryToken 为静态 Bearer token，存在时直接使用，不走换 token 流程
	RegistryToken string
}

func (c Credential) String() string { return "<redacted>" }

type dockerConfig struct {
	Auths map[string]dockerAuth `json:"auths"`
}

type dockerAuth struct {
	Username      string `json:"username"`
	Password      string `json:"password"`
	Auth          string `json:"auth"`
	IdentityToken string `json:"identitytoken"`
	RegistryToken string `json:"registrytoken"`
}

// LoadCredentials 读取 docker config.json 格式的上游凭证，返回 主机名（小写，含端口） → 凭证。
// auths 的键可以是主机名，也可以是带协议的 URL。
func LoadCredentials(path string) (map[string]Credential, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read upstream docker config: %w", err)
	}
	var cfg dockerConfig
	if err := json.Unmarshal(raw, &cfg); err != nil {
		// json 错误信息可能带出文件片段，只返回位置无关的描述
		return nil, errors.New("parse upstream docker config: invalid JSON")
	}
	out := map[string]Credential{}
	for key, a := range cfg.Auths {
		host := hostOfAuthKey(key)
		if host == "" {
			return nil, fmt.Errorf("upstream docker config: invalid auths key %q", key)
		}
		cred, err := a.credential()
		if err != nil {
			return nil, fmt.Errorf("upstream docker config: auths[%q]: %w", key, err)
		}
		if _, dup := out[host]; dup {
			return nil, fmt.Errorf("upstream docker config: duplicated credentials for host %q", host)
		}
		out[host] = cred
	}
	return out, nil
}

func hostOfAuthKey(key string) string {
	key = strings.TrimSpace(key)
	if strings.Contains(key, "://") {
		u, err := url.Parse(key)
		if err != nil {
			return ""
		}
		return strings.ToLower(u.Host)
	}
	host, _, _ := strings.Cut(key, "/")
	return strings.ToLower(host)
}

func (a dockerAuth) credential() (Credential, error) {
	switch {
	case a.IdentityToken != "":
		return Credential{}, errors.New("identitytoken is not supported, use username/password or registrytoken")
	case a.RegistryToken != "":
		return Credential{RegistryToken: a.RegistryToken}, nil
	case a.Username != "" || a.Password != "":
		return Credential{Username: a.Username, Password: a.Password}, nil
	case a.Auth != "":
		decoded, err := base64.StdEncoding.DecodeString(a.Auth)
		if err != nil {
			return Credential{}, errors.New("auth is not valid base64")
		}
		user, pass, ok := strings.Cut(string(decoded), ":")
		if !ok {
			return Credential{}, errors.New("auth is not username:password")
		}
		return Credential{Username: user, Password: pass}, nil
	default:
		return Credential{}, errors.New("no username/password, auth or registrytoken")
	}
}
