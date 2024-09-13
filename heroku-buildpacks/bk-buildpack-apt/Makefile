.DEFAULT_GOAL:=help
ROOT ?= $(CURDIR)

${ROOT}/output:
	mkdir -p ${ROOT}/output


##@ Build

.PHONY: clean
clean:  ## 清理产物
	rm -rf ${ROOT}/output

.PHONY: pack
pack: ${ROOT}/output  ## 打包 buildpack
	$(eval name ?= bk-buildpack-apt-${version}.tar)
	cd buildpack && tar cvhf ${ROOT}/output/${name} --exclude=test *


.PHONY: help
help:  ## 打印帮助信息
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
