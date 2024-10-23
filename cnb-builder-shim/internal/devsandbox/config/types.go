package config

// 源码获取方式
type FetchMethod string

const (
	HTTP    FetchMethod = "HTTP"
	BK_REPO FetchMethod = "BK_REPO"
	GIT     FetchMethod = "GIT"
)

// SourceCodeConfig 源码配置
type SourceCodeConfig struct {
	// 源码获取方式
	FetchMethod FetchMethod
	// 源码地址
	FetchUrl string
	// Git 仓库版本
	GitRevision string
	// 工作目录
	Workspace string
}

// Config  全局配置
type Config struct {
	// 源码配置
	SourceCode SourceCodeConfig
}
