.DEFAULT_GOAL:=help
ROOT ?= $(CURDIR)

${ROOT}/output:
	mkdir -p ${ROOT}/output


##@ Build

.PHONY: clean
clean:  ## 清理产物
	rm -rf ${ROOT}/output

.PHONY: pack
pack: ${ROOT}/output patch  ## 打包 buildpack
	$(eval name ?= bk-buildpack-nodejs-${version}.tar)
	cd buildpack && tar cvhf ${ROOT}/output/${name} --exclude=test *
	make unpatch


##@ Misc
.PHONY: patch
patch:
	patch buildpack/bin/compile patchs/buildpack/bin/compile.patch
	patch buildpack/lib/binaries.sh patchs/buildpack/lib/binaries.sh.patch
	patch buildpack/lib/cache.sh patchs/buildpack/lib/cache.sh.patch
	patch buildpack/lib/dependencies.sh patchs/buildpack/lib/dependencies.sh.patch
	patch buildpack/lib/monitor.sh patchs/buildpack/lib/monitor.sh.patch
	ln -s ../hooks buildpack/hooks


.PHONY: unpatch
unpatch:
	patch -R buildpack/bin/compile patchs/buildpack/bin/compile.patch
	patch -R buildpack/lib/binaries.sh patchs/buildpack/lib/binaries.sh.patch
	patch -R buildpack/lib/cache.sh patchs/buildpack/lib/cache.sh.patch
	patch -R buildpack/lib/dependencies.sh patchs/buildpack/lib/dependencies.sh.patch
	patch -R buildpack/lib/monitor.sh patchs/buildpack/lib/monitor.sh.patch
	rm buildpack/hooks


.PHONY: help
help:  ## 打印帮助信息
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)