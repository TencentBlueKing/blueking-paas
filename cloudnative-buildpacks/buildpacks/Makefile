.DEFAULT_GOAL:=help

##@ Build
.PHONY: all
all:  bk-buildpack-python bk-buildpack-nodejs bk-buildpack-go ## 构建所有 buildpack

.PHONY: bk-buildpack-python
bk-buildpack-python: ## 构建 python buildpack
	cd bk-buildpack-python && make package

.PHONY: bk-buildpack-nodejs
bk-buildpack-nodejs: ## 构建 nodejs buildpack
	cd bk-buildpack-nodejs && make package

.PHONY: bk-buildpack-go
bk-buildpack-go: ## 构建 go buildpack
	cd bk-buildpack-go && make package


##@ Misc
.PHONY: help
help:  ## 打印帮助信息
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
