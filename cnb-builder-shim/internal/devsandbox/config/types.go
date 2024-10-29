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

// CorsConfig 跨域配置
type CorsConfig struct {
	// 允许的来源
	AllowOrigins []string
	// 允许的HTTP方法
	AllowMethods []string
	// 允许的请求头
	AllowHeaders []string
	// 暴露的响应头
	ExposeHeaders []string
	// 凭证共享
	AllowCredentials bool
}

// ServiceConfig 服务配置
type ServiceConfig struct {
	// 源码获取方式
	Cors CorsConfig
}

// Config  全局配置
type Config struct {
	// 源码配置
	SourceCode SourceCodeConfig
	// 服务配置
	Service ServiceConfig
}
