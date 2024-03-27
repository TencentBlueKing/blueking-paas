<template>
  <div class="app-success-wrapper">
    <div class="container biz-create-success">
      <paas-plugin-title :no-shadow="true" />
      <div class="success-wrapper">
        <div class="info">
          <p>
            <i class="paasng-icon paasng-check-1 text-success" />
          </p>
          <p>{{ $t('恭喜，插件') }} - {{ extraInfo.name }} "{{ extraInfo.pluginName }}"&nbsp;&nbsp;{{ $t('创建成功') }}</p>
          <p>
            <bk-button
              :theme="'primary'"
              class="mr10"
              @click="handlePageJump('pluginSummary')"
            >
              {{ $t('插件概览') }}
            </bk-button>
            <bk-button
              :theme="'default'"
              type="submit"
              @click="handlePageJump('test')"
            >
              {{ isTestVersion ? $t('测试插件') : $t('新建版本') }}
            </bk-button>
          </p>
        </div>
        <!-- 内容 -->
        <section class="content">
          <p class="log-title">
            {{ $t('开发指引') }}
          </p>
          <div class="tips-wrapper">
            <div class="title">
              {{ $t('拉取代码到本地') }}
              <div
                class="icon-wrapper"
                v-copy="gitClone"
              >
                <i
                  :class="[
                    'paasng-icon',
                    'paasng-general-copy',
                    localLanguage === 'en' ? 'copy-icon-en' : 'copy-icon',
                  ]"
                />
                {{ $t('复制') }}
              </div>
            </div>
            <!-- 代码仓库地址 -->
            <div class="tips line">
              <code>
                <p>{{ gitClone }}</p>
              </code>
            </div>
            <div class="title mt10">
              {{ $t('提交代码到代码库') }}
              <div
                class="icon-wrapper"
                v-copy="pushTips"
              >
                <i
                  :class="[
                    'paasng-icon',
                    'paasng-general-copy',
                    'copy-icon',
                    localLanguage === 'en' ? 'copy-icon-two' : '',
                  ]"
                />
                {{ $t('复制') }}
              </div>
            </div>
            <div class="tips line">
              <code>
                <p>{{ pushTips }}</p>
              </code>
            </div>
            <div class="title mt10">
              {{ $t('创建测试版本进行测试，创建正式版本进行发布') }}
            </div>
          </div>
          <div class="plugin-guide">
            <a
              target="_blank"
              :href="extraInfo.docs"
            >
              {{ $t('查看更多开发和发布指引') }}
              <i class="paasng-icon paasng-double-arrow-right" />
            </a>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script>
import paasPluginTitle from '@/components/pass-plugin-title';
export default {
  components: {
    paasPluginTitle,
  },
  data() {
    return {
      extraInfo: {},
      pluginInfo: {},
    };
  },
  computed: {
    gitClone() {
      return `git clone "${this.pluginInfo?.repository}"`;
    },
    // 提交到代码仓库
    pushTips() {
      return [
        'git add .',
        'git commit -m "Your modified content"',
        'git push',
      ].join('\n');
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    pluginId() {
      return this.$route.params.id;
    },
    // 插件类型id
    pluginTypeId() {
      return this.$route.params.pluginTypeId;
    },
    isTestVersion() {
      return this.pluginInfo.has_test_version;
    },
  },
  created() {
    this.init();
  },
  mounted() {
    const objectKey = localStorage.getItem(this.$route.query.key) === 'undefined'
      ? ''
      : localStorage.getItem(this.$route.query.key);
    this.extraInfo = JSON.parse(objectKey || '{}');
  },
  methods: {
    async init() {
      try {
        const res = await this.$store.dispatch('plugin/getPluginInfo', { pluginId: this.pluginId, pluginTypeId: this.pluginTypeId });
        this.pluginInfo = res;
      } catch (e) {
        console.error(e);
      }
    },
    handlePageJump(key) {
      let name = key;
      let query = {};
      if (name === 'test') {
        name = this.isTestVersion ? 'pluginVersionManager' : 'pluginVersionEditor';
        query = {
          type: this.isTestVersion ? 'test' : 'prod',
        };
      }
      this.$router.push({
        name,
        params: {
          pluginTypeId: this.pluginTypeId,
          id: this.pluginId,
        },
        query,
      });
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
    padding: 66px 0 20px 0;
  }
  .success-wrapper {
    margin-top: 16px;
    .info,
    .content {
      background: #ffffff;
      box-shadow: 0 2px 4px 0 #1919290d;
      border-radius: 2px;
    }

    .content {
      margin-top: 16px;
      padding: 24px 40px;
    }
  }
}
.success-wrapper {
  width: 100%;
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
      margin-top: 16px;
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
    .log-title {
      color: #313238;
      font-weight: bold;
    }
  }
}

.tips-wrapper {
  border-radius: 3px;
  padding: 16px;
  padding-right: 0;
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
      .copy-icon,
      .copy-icon-en {
        transform: translateY(0px);
        font-size: 16px;
        margin-right: 3px;
      }
    }
    &::before {
      position: absolute;
      content: '';
      width: 9px;
      height: 9px;
      top: 5px;
      left: -15px;
      border: 2px solid #d8d8d8;
      border-radius: 50%;
      z-index: 1;
    }
  }
  .line::before {
    position: absolute;
    box-sizing: content-box;
    content: '';
    width: 1px;
    height: calc(100% + 11px);
    top: -13px;
    left: -11px;
    background: #d8d8d8;
    padding-bottom: 18px;
  }
  .tips-plugin.line::before {
    padding-bottom: 70px;
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
      word-break: break-all;
      white-space: pre-line;
      background: 0 0;
      box-sizing: inherit;
      font-family: MicrosoftYaHei;
      font-size: 14px;
      color: #313238;
    }
  }
  .tips-plugin {
    margin-bottom: 16px;
  }
}

.plugin-guide {
  display: flex;
  flex-direction: row-reverse;
  i {
    font-weight: 700;
    font-size: 14px;
  }
}
</style>
