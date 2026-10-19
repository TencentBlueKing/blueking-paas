package upstream

import (
	"fmt"
	"regexp"
	"strings"
)

var aliasRE = regexp.MustCompile(`^[a-z0-9]+(-+[a-z0-9]+)*$`)

// AliasOf 由上游主机名（含端口）推导别名：转小写后把 "." 与 ":" 替换为 "-"。
// apiserver 按同一规则推导，二者必须一致。
func AliasOf(host string) (string, error) {
	if host == "" {
		return "", fmt.Errorf("empty host")
	}
	if strings.HasPrefix(host, "[") {
		return "", fmt.Errorf("IPv6 literal host %q is not supported", host)
	}
	alias := strings.NewReplacer(".", "-", ":", "-").Replace(strings.ToLower(host))
	if !aliasRE.MatchString(alias) {
		return "", fmt.Errorf("host %q does not derive a valid alias (got %q)", host, alias)
	}
	return alias, nil
}
