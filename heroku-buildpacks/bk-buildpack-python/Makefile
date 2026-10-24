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
	$(eval name ?= bk-buildpack-python-${version}.tar)
	cd buildpack && tar cvhf ${ROOT}/output/${name} --exclude=test *
	make unpatch

##@ Test

.PHONY: test
test:  ## 单元测试 - 执行前需要先 patch
	docker run --rm \
			--network=host \
			-v `pwd`:/data \
			-w /data \
			bats/bats:v1.4.1 \
			/data/tests


.PHONY: integration-test
integration-test:  ## 集成测试
	cd integration && make all


##@ Misc
.PHONY: lint-in-container
lint-in-container:
	docker run --rm -it \
			--network=host \
			-v `pwd`:/data \
			pipelinecomponents/shellcheck \
			bash -c "shellcheck -s bash -e SC2034,SC2154,SC2206 \$$(grep -l '^#!/usr/bin/env bash' /data/hooks/*) && echo good job"

.PHONY: lint
lint:
	@shellcheck -s bash -e SC2034,SC2154,SC2206 $$(grep -l '^#!/usr/bin/env bash' hooks/*) && echo good job


.PHONY: update
update: unpatch ## 更新 buildpack
        git subtree pull --prefix buildpack https://github.com/heroku/heroku-buildpack-python.git main


.PHONY: patch
patch: 
	patch buildpack/bin/compile patches/buildpack/bin/compile.patch
	patch buildpack/lib/python.sh patches/buildpack/lib/python.sh.patch
	patch buildpack/lib/uv.sh patches/buildpack/lib/uv.sh.patch
	patch buildpack/lib/pip.sh patches/buildpack/lib/pip.sh.patch
	patch buildpack/lib/poetry.sh patches/buildpack/lib/poetry.sh.patch
	patch buildpack/lib/pipenv.sh patches/buildpack/lib/pipenv.sh.patch
	rsync -a --delete ./hooks buildpack/


.PHONY: unpatch
unpatch:
	patch -R buildpack/bin/compile patches/buildpack/bin/compile.patch
	patch -R buildpack/lib/python.sh patches/buildpack/lib/python.sh.patch
	patch -R buildpack/lib/uv.sh patches/buildpack/lib/uv.sh.patch
	patch -R buildpack/lib/pip.sh patches/buildpack/lib/pip.sh.patch
	patch -R buildpack/lib/poetry.sh patches/buildpack/lib/poetry.sh.patch
	patch -R buildpack/lib/pipenv.sh patches/buildpack/lib/pipenv.sh.patch
	rm -r buildpack/hooks


.PHONY: help
help:  ## 打印帮助信息
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
