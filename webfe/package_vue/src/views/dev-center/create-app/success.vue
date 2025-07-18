<!-- 源码库为 bare_svn、bk_svn 的创建成功页面 -->
<template lang="html">
  <div class="app-success-wrapper">
    <top-bar />
    <div class="container biz-create-success">
      <div class="success-wrapper">
        <div class="info">
          <p>
            <i class="paasng-icon paasng-check-1 text-success" />
          </p>
          <p>{{ $t('恭喜，应用') }}&nbsp;&nbsp;"{{ application.name }}"&nbsp;&nbsp;{{ $t('创建成功') }}</p>
          <p>
            <bk-button
              :theme="'primary'"
              class="mr10"
              @click="handlePageJump('cloudAppDeployManageStag')"
            >
              {{ $t('部署应用') }}
            </bk-button>
            <bk-button
              :theme="'default'"
              type="submit"
              @click="handlePageJump('cloudAppDeployForBuild')"
            >
              {{ $t('模块配置') }}
            </bk-button>
          </p>
        </div>
        <div class="content">
          <div class="input-wrapper">
            <div class="input-item">
              <input
                v-model="trunkURL"
                class="ps-form-control svn-input"
                type="text"
                readonly
                style="background: #fff"
              />
            </div>
            <div class="btn-item">
              <a
                class="btn-checkout ps-btn ps-btn-primary"
                :href="trunkURL"
              >
                {{ $t('签出代码') }}
              </a>
            </div>
          </div>
        </div>
        <section
          class="doc-panel"
          v-if="advisedDocLinks.length > 0"
        >
          <template>
            <p class="help-doc">
              {{ $t('帮助文档') }}
            </p>
            <p
              v-for="(link, linkIndex) in advisedDocLinks"
              :key="linkIndex"
              class="doc-item"
            >
              <a
                :href="link.location"
                :title="link.short_description"
                target="_blank"
              >
                {{ link.title }}
              </a>
            </p>
          </template>
        </section>
      </div>
    </div>
  </div>
</template>

<script>
import topBar from './comps/top-bar.vue';
export default {
  components: {
    topBar,
  },
  data() {
    const appCode = this.$route.params.id;
    return {
      appCode: appCode,
      application: {},
      trunkURL: '',
      advisedDocLinks: [],
    };
  },
  computed: {
    pluginTips: function () {
      return ['pip install cookiecutter', `cookiecutter ${this.GLOBAL.LINK.BK_PLUGIN_TEMPLATE}`].join('\n');
    },
  },
  created() {
    const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/`;
    this.$http.get(url).then((response) => {
      const body = response;
      this.application = body.application;

      const repo = this.application.modules.find((module) => module.is_default).repo;
      this.trunkURL = repo.trunk_url;
      this.$nextTick(() => {
        const el = document.querySelector('.content');
        // 没有子元素隐藏当前容器
        this.hideNotChildElement(el);
      });
    });
    this.getDocLinks();
  },
  methods: {
    // 获取文档链接信息
    async getDocLinks() {
      try {
        const res = await this.$store.dispatch('deploy/getAppDocLinks', {
          appCode: this.appCode,
          params: {
            plat_panel: 'app_created',
            limit: 3,
          },
        });
        this.advisedDocLinks = res.links;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    handlePageJump(name) {
      this.$router.push({
        name,
        params: {
          id: this.appCode,
          moduleId: 'default',
        },
      });
    },
    hideNotChildElement(el) {
      const childNodes = el.childNodes;

      // 判断子元素是否存在
      const allChildNodes = Array.from(childNodes).filter((node) => node.nodeType !== 8); // 过滤掉注释节点
      if (allChildNodes.length === 0) {
        el.style.display = 'none'; // 隐藏当前元素
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.app-success-wrapper {
  width: 100%;
  height: 100%;
  min-height: 100vh;
  background: #f5f7fa;

  .biz-create-success {
    background: #f5f7fa;
    padding: 76px 0 20px 0;
  }
  .success-wrapper {
    .info,
    .content,
    .doc-panel {
      background: #ffffff;
      box-shadow: 0 2px 4px 0 #1919290d;
      border-radius: 2px;
    }

    .content {
      margin-top: 16px;
      padding: 24px 40px;
    }

    .doc-panel {
      padding: 24px 40px;
      margin-top: 16px;
      .help-doc {
        margin-bottom: 10px;
        color: #63656e;
        font-weight: bold;
      }
      .doc-item {
        line-height: 32px;
      }
    }
  }
}
.tips-wrapper {
  border-radius: 3px;
  padding: 16px;
  overflow: auto;
  font-size: 85%;
  line-height: 1.45;
  .title {
    position: relative;
    font-size: 14px;
    color: #63656e;
    margin-bottom: 6px;
    .icon-wrapper {
      position: absolute;
      top: 1px;
      right: 0px;
      display: flex;
      align-items: center;
      color: #3a84ff;
      cursor: pointer;
      font-size: 14px;
      .copy-icon {
        font-size: 16px;
        margin-right: 3px;
      }
    }
  }
  .tips {
    position: relative;
    padding: 12px 16px;
    border-radius: 2px;
    background: #f5f7fa;
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
      font-family: MicrosoftYaHei;
      font-size: 14px;
      color: #313238;
    }
  }
}
.success-wrapper {
  width: 100%;
  border-radius: 2px;
  .info {
    padding-top: 45px;
    padding-bottom: 40px;
    p:nth-child(1) {
      margin: 0 auto;
      width: 84px;
      height: 84px;
      border-radius: 50%;
      text-align: center;
      background: #e5f6ea;
      .text-success {
        font-weight: bold;
        line-height: 84px;
        transform: scale(2);
        font-size: 20px;
        color: #3fc06d;
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
    .input-wrapper {
      display: table;
      width: 100%;
      .input-item {
        display: table-cell;
        width: 80%;
        .svn-input {
          box-sizing: border-box;
          position: relative;
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
  }
}
</style>
