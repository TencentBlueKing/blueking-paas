# 把 uv.lock 中来自公网 PyPI 的包改为从镜像下载，其余内容原样输出。
#
# usage: BK_UV_MIRROR=<镜像 simple 地址> BK_UV_MIRROR_FILES=<镜像包文件前缀> awk -f uv-lock-mirror.awk uv.lock
#
# 只改 source 为公网 PyPI 的 [[package]]：项目自身、direct URL 依赖、私有索引来的包都不动，
# 否则 uv sync --locked 会认为锁文件与 pyproject.toml 不一致。哈希原样保留，镜像内容不对只会校验失败。
# 地址从环境变量读（awk -v 会解析反斜杠转义），再用 index/substr 做字面替换，& # \ 等字符都不需要转义。

function replace_all(text, from, to,    out, pos) {
	out = ""
	while ((pos = index(text, from)) > 0) {
		out = out substr(text, 1, pos - 1) to
		text = substr(text, pos + length(from))
	}
	return out text
}

function flush() {
	if (from_pypi) {
		block = replace_all(block, PYPI_REGISTRY, "registry = \"" mirror "\"")
		block = replace_all(block, PYPI_FILES, files "/")
	}

	printf "%s", block
	block = ""
	from_pypi = 0
}

BEGIN {
	PYPI_REGISTRY = "registry = \"https://pypi.org/simple\""
	PYPI_FILES = "https://files.pythonhosted.org/packages/"
	mirror = ENVIRON["BK_UV_MIRROR"]
	files = ENVIRON["BK_UV_MIRROR_FILES"]
}

/^\[\[package\]\]$/ {
	flush()
}

{
	block = block $0 "\n"
	if (index($0, "source = { " PYPI_REGISTRY " }") == 1) {
		from_pypi = 1
	}
}

END {
	flush()
}
