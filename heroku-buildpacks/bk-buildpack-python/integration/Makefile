.DEFAULT_GOAL:=help
ROOT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))


.PHONY: pack
pack:
	cd .. && make pack version=debug

.PHONY: all
all: build-fastapi build-bkframework
	echo "successful"


##@ Test
.PHONY: build-fastapi
build-fastapi: pack  ## 测试构建 FastAPI 应用
	docker run --rm --privileged --name bk-saas-pack -d \
		-v ${ROOT_DIR}/build-fastapi/testdata:/data \
		-v ${ROOT_DIR}/../output/bk-buildpack-python-debug.tar:/buildpack/bk-buildpack-python-debug.tar \
		mirrors.tencent.com/bkpaas/bk-saas-pack:debug
	docker exec bk-saas-pack expect testcase
	docker stop bk-saas-pack


.PHONY: build-bkframework
build-bkframework: pack  ## 测试构建 Python 应用
	docker run --rm --privileged --name bk-saas-pack -d \
		-v ${ROOT_DIR}/build-bkframework/testdata:/data \
		-v ${ROOT_DIR}/../output/bk-buildpack-python-debug.tar:/buildpack/bk-buildpack-python-debug.tar \
		mirrors.tencent.com/bkpaas/bk-saas-pack:debug
	docker exec bk-saas-pack expect testcase
	docker stop bk-saas-pack


##@ Misc
.PHONY: help
help:  ## 打印帮助信息
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)