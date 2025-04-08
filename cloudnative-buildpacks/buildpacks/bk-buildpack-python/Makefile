.DEFAULT_GOAL:=help
ROOT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
NAME := bk-buildpack-python
VERSION := v213


##@ Build
.PHONY: package
package: package-heroku-buildpack ## 将 cnb buildpack 打包
	cp shim/* cnb-buildpack/bin/
	tar -xvf target/output/bk-buildpack-python-${VERSION}.tar -C cnb-buildpack/target
	tar -zcvf $(NAME)-$(VERSION).tgz cnb-buildpack


.PHONY: package-heroku-buildpack
package-heroku-buildpack: init-submodule ## 打包 heroku-buildpack
	cd target && make pack version=$(VERSION)


.PHONY: init-submodule
init-submodule:
	git submodule update --init


.PHONY: help
help:
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
