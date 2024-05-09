.DEFAULT_GOAL:=help
ROOT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
NAME := bk-buildpack-apt
VERSION := v2

##@ Build
.PHONY: package
package: package-heroku-buildpack ## package the buildpack
	cp shim/* cnb-buildpack/bin/
	tar -xvf target/output/bk-buildpack-apt-${VERSION}.tar -C cnb-buildpack/target
	pack buildpack package $(NAME)-$(VERSION).cnb -p cnb-buildpack/ -f file

.PHONY: package-heroku-buildpack
package-heroku-buildpack: init-submodule ## 打包 heroku-buildpack
	cd target && make pack version=${VERSION}


.PHONY: init-submodule
init-submodule:
	git submodule update --init


.PHONY: help
help:
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
