help: ## 展示可用 make 命令及说明
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ 环境初始化

init-pre-commit: ## 初始化 pre-commit
	pip install pre-commit
	pre-commit install

init-py-dep: ## 初始化 python 依赖包
	pip install poetry==1.5.1
	poetry install

init-node-dep: ## 初始化 nodejs
	npm install

init-all: init-pre-commit init-py-dep init-node-dep ## 初始化所有环境

##@ 研发命令（后端）

dj-settings: ## 设置 DJANGO_SETTINGS_MODULE
  export DJANGO_SETTINGS_MODULE=paasng.settings

test: dj-settings ## 执行项目单元测试（pytest）
	pytest --maxfail=5 -l --reuse-db paasng

server: dj-settings ## 执行 runserver 命令
	python paasng/manage.py runserver

celery: dj-settings ## 启用 celery worker
	cd paasng && celery -A paasng worker -l debug

##@ 研发命令（国际化）

i18n-po: dj-settings ## 将 Python 以及 Django 模版中的 message 采集到 django.po
	python paasng/manage.py makemessages -d django -l en -e html,part -e py
	python paasng/manage.py makemessages -d django -l zh_Hans -e html,part -e py

i18n-mo: dj-settings ## 将 django.po 文件编译成 django.mo 文件
	python paasng/manage.py compilemessages

i18n-all: i18n-po i18n-mo  ## 执行 i18n-po & i18n-mo

##@ 研发命令（admin42）

npm-build: ## 执行 npm run build
	npm run build

collectstatic: dj-settings ## 执行 collectstatic
	python paasng/manage.py collectstatic
