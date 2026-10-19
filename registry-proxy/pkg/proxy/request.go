package proxy

import (
	"errors"
	"io"
	"net/url"
)

// singleValueParams 是代理据以判定路由与授权的查询参数。代理只读取第一个值，
// 而上游可能取最后一个，出现多次时无法保证上游执行的就是代理检查过的值
var singleValueParams = []string{"digest", "mount", "from"}

// parseQuery 解析客户端查询串。代理看到的参数与上游看到的必须一致，以下情况直接拒绝：
//   - 无法完整解析：r.URL.Query() 会静默丢弃含 ; 等的片段，而上游或其前置网关可能仍把 ; 当作分隔符；
//   - singleValueParams 中的参数出现多次。
func parseQuery(raw string) (url.Values, error) {
	query, err := url.ParseQuery(raw)
	if err != nil {
		return nil, err
	}
	for _, k := range singleValueParams {
		if len(query[k]) > 1 {
			return nil, errors.New("duplicate query parameter " + k)
		}
	}
	return query, nil
}

// countingBody 统计客户端请求体的字节数，供审计与指标使用
type countingBody struct {
	io.ReadCloser
	n int64
}

func (b *countingBody) Read(p []byte) (int, error) {
	n, err := b.ReadCloser.Read(p)
	b.n += int64(n)
	return n, err
}
