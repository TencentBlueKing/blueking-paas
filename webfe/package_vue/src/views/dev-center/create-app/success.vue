<template lang="html">
  <div class="container biz-create-success">
    <div class="success-wrapper">
      <div class="info">
        <p>
          <i class="paasng-icon paasng-check-circle-shape text-success" />
        </p>
        <p>{{ $t('恭喜，应用') }}&nbsp;&nbsp;"{{ application.name }}"&nbsp;&nbsp;{{ $t('创建成功') }}</p>
        <p>
          {{ $t('常用操作：') }}
          <router-link
            :to="{ name: 'appSummary', params: { id: appCode } }"
            class="link"
          >
            {{ $t('查看应用概览') }}
          </router-link>
          <span class="success-dividing-line">|</span>
          <router-link
            :to="{ name: 'appDeploy', params: { id: appCode } }"
            class="link"
          >
            {{ $t('部署应用') }}
          </router-link>
          <span class="success-dividing-line">|</span>
          <router-link
            :to="{ name: 'appRoles', params: { id: appCode } }"
            class="link"
          >
            {{ $t('添加成员') }}
          </router-link>
        </p>
      </div>
      <div class="content">
        <div
          v-if="application.config_info.require_templated_source"
          class="input-wrapper"
        >
          <div class="input-item">
            <input
              v-model="trunkURL"
              class="ps-form-control svn-input"
              type="text"
              readonly
              style="background: #fff;"
            >
          </div>
          <div class="btn-item">
            <a
              class="btn-checkout ps-btn ps-btn-primary"
              :href="trunkURL"
            > {{ $t('签出代码') }} </a>
          </div>
        </div>
        <div
          v-if="application.type === 'bk_plugin'"
          class="btn-check-svn spacing-x4"
        >
          <div class="tips-wrapper">
            <div class="tips">
              <code> {{ $t('初始化插件项目') }} {{ pluginTips }}
              </code>
              <i
                v-copy="pluginTips"
                class="paasng-icon paasng-general-copy copy-icon"
              />
            </div>
          </div>
        </div>
        <template v-if="advisedDocLinks.length > 0">
          <p class="help-doc">
            {{ $t('帮助文档') }}
          </p>
          <p
            v-for="(link, linkIndex) in advisedDocLinks"
            :key="linkIndex"
          >
            <a
              :href="link.location"
              :title="link.short_description"
              target="_blank"
            >{{ link.title }}</a>
          </p>
        </template>
      </div>
    </div>
  </div>
</template>

<script>
    export default {
        data () {
            const appCode = this.$route.params.id;
            return {
                appCode: appCode,
                application: {},
                trunkURL: '',
                advisedDocLinks: []
            };
        },
        computed: {
            pluginTips: function () {
                return [
                    'pip install cookiecutter',
                    `cookiecutter ${this.GLOBAL.LINK.BK_PLUGIN_TEMPLATE}`
                ].join('\n');
            }
        },
        created () {
            const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/`;
            const linkUrl = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/accessories/advised_documentary_links/?plat_panel=app_created&limit=3`;
            this.$http.get(url).then((response) => {
                const body = response;
                this.application = body.application;

                const repo = this.application.modules.find(module => module.is_default).repo;
                this.trunkURL = repo.trunk_url;
            });
            this.$http.get(linkUrl).then((response) => {
                this.advisedDocLinks = response.links;
            });
        }
    };
</script>

<style lang="scss" scoped>
    .biz-create-success {
        padding: 120px 0 20px 0;
    }
    .tips-wrapper {
        background-color: #f7f7f7;
        border-radius: 3px;
        padding: 16px;
        overflow: auto;
        font-size: 85%;
        line-height: 1.45;
        .tips {
            position: relative;
            &:first-child {
                margin-bottom: 16px;
                .copy-icon {
                    left: 165px;
                }
            }
            code {
                display: inline;
                max-width: initial;
                padding: 0;
                margin: 0;
                overflow: initial;
                line-height: 22px;
                word-wrap: normal;
                background-color: transparent;
                border: 0;
                font-size: 100%;
                word-break: normal;
                white-space: pre-line;
                background: 0 0;
                box-sizing: inherit;
                color: #24292e;
            }
            .copy-icon {
                position: absolute;
                left: 175px;
                cursor: pointer;
                font-size: 20px;
                top: 1px;
                &:hover {
                    color: #3a84ff;
                }
            }
        }
    }
    .success-wrapper {
        width: 100%;
        height: 520px;
        border: 1px solid #dcdee5;
        border-radius: 2px;
        .info {
            padding-top: 45px;
            height: 200px;
            border-bottom: 1px solid #dcdee5;
            p:nth-child(1) {
                text-align: center;
                .text-success {
                    font-size: 49px;
                    color: #2dcb56;
                }
            }
            p:nth-child(2) {
                margin-top: 16px;
                font-size: 16px;
                font-weight: bold;
                color: #313238;
                text-align: center;
            }
            p:nth-child(3) {
                margin-top: 12px;
                font-size: 14px;
                color: #63656e;
                text-align: center;
                .link {
                    color: #3a84ff;
                    cursor: pointer;
                    &:hover {
                        color: #699df4;
                    }
                }
            }
        }
        .content {
            padding: 40px 60px;
            .input-wrapper {
                display: table;
                width: 100%;
                .input-item {
                    display: table-cell;
                    width: 80%;
                    .svn-input {
                        box-sizing: border-box;
                        position: relative;
                        top: -1px;
                        width: 100%;
                        height: 31px;
                        border-right: 0;
                    }
                }
                .btn-item {
                    display: table-cell;
                    width: 15%;
                    .btn-checkout {
                        width: 100%;
                        box-sizing: border-box;
                        border-radius: 0 2px 2px 0;
                    }
                }
            }
            .view-svn {
                margin-top: 7px;
            }
            .help-doc {
                margin: 37px 0 10px 0;
                color: #63656e;
                font-weight: bold;
            }
        }
    }
</style>
