<template lang="html">
  <div class="cloud-wrapper">
    <!-- 云原生应用没有头部导航 -->
    <div :class="['ps-top-bar', 'cloud-api-permission', { 'plugin-top-bar': isPlugin }]">
      <div class="header-title">
        {{ $t('云 API 权限') }}
        <div
          class="guide-wrapper"
          v-if="userFeature.APP_ACCESS_TOKEN"
        >
          <bk-button
            class="f12"
            theme="primary"
            :outline="true"
            v-bk-tooltips="createNewTokenTips"
            @click="handleShowDialogCreateToken"
          >
            {{ $t('创建新令牌') }}
          </bk-button>
        </div>
      </div>
    </div>
    <div class="tab-container-cls">
      <section class="app-container middle cloud-container">
        <paas-content-loader
          :key="pageKey"
          :is-loading="isLoading"
          placeholder="cloud-api-index-loading"
          :offset-top="12"
          :delay="1000"
        >
          <bk-button
            class="gateway-guide"
            text
            theme="primary"
            @click="toLink('gateway')"
          >
            {{ $t('API 调用指引') }}
            <i class="paasng-icon paasng-jump-link"></i>
          </bk-button>
          <bk-tab
            :active.sync="active"
            type="unborder-card"
            ext-cls="paas-custom-tab-card-grid"
            @tab-change="handleTabChange"
          >
            <bk-tab-panel
              v-for="(panel, index) in displayPanels"
              :key="index"
              v-bind="panel"
            />
            <div class="cloud-type-item">
              <component
                :is="activeComponent"
                :key="comKey"
                :app-code="appCode"
                :api-type="apiType"
                :type-list="typeList"
                @data-ready="handlerDataReady"
              />
            </div>
          </bk-tab>
        </paas-content-loader>
      </section>
    </div>

    <!-- 创建新令牌 -->
    <bk-dialog
      v-model="createTokenCofig.visible"
      theme="primary"
      :mask-close="false"
      width="680"
      @after-leave="handleCancel"
    >
      <div
        class="header-wrapper"
        slot="header"
      >
        {{ $t('创建新令牌') }}
      </div>
      <div class="steps-wrapper">
        <bk-steps
          ext-cls="custom-icon"
          :steps="steps"
          :cur-step.sync="curStep"
        ></bk-steps>
      </div>
      <section
        class="create-dialog-wrapper"
        v-if="curStep === 1"
      >
        <bk-alert
          ext-cls="custom-alert-cls"
          type="error"
          :show-icon="false"
        >
          <div
            slot="title"
            class="alert-wrapper"
          >
            <i class="paasng-icon paasng-remind error" />
            {{ $t('创建新令牌( access_token)，会导致原来的 access_token 会失效，该操作不可撤销，请谨慎操作。') }}
            <a
              target="_blank"
              :href="GLOBAL.DOC.ACCESS_TOKEN_USAGE_GUIDE"
            >
              {{ $t('使用指引') }}
            </a>
          </div>
        </bk-alert>
        <div class="content">
          <p class="title">{{ createTokenTip }}</p>
          <bk-input v-model="curAppId"></bk-input>
        </div>
      </section>
      <section
        class="create-dialog-wrapper"
        v-bkloading="{ isLoading: nextBtnLoading, zIndex: 10 }"
        v-else
      >
        <bk-alert
          v-if="tokenUrl"
          ext-cls="custom-alert-cls"
          type="success"
          :show-icon="false"
        >
          <div
            slot="title"
            class="alert-wrapper"
          >
            <i class="paasng-icon paasng-pass success" />
            {{ $t('令牌（access_token）创建成功！请复制该令牌，关闭弹窗后将无法再次看到它。') }}
          </div>
        </bk-alert>
        <div class="content">
          <p
            class="title"
            v-if="tokenUrl"
          >
            {{ localLanguage === 'en' ? 'Access_token' : '令牌（access_token）' }}
          </p>
          <div
            :class="['access-token-url', { error: !tokenUrl }]"
            v-copy="tokenUrl"
          >
            <span v-if="tokenUrl">{{ tokenUrl }}</span>
            <span v-else>{{ errorObject?.message }}</span>
            <div
              class="copy"
              v-if="tokenUrl"
            >
              <i class="paasng-icon paasng-general-copy" />
              {{ $t('复制') }}
            </div>
          </div>
        </div>
      </section>
      <div
        class="footer-wrapper"
        slot="footer"
      >
        <bk-button
          v-if="curStep === 1"
          :theme="'primary'"
          :disabled="nextBtnDisabled"
          :loading="nextBtnLoading"
          @click="handleNext"
        >
          {{ $t('下一步') }}
        </bk-button>
        <bk-button
          v-else
          :theme="'primary'"
          @click="handleCancel"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button
          class="ml-8"
          :theme="'default'"
          @click="handleCancel"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
    </bk-dialog>
  </div>
</template>

<script>
import appBaseMixin from '@/mixins/app-base-mixin';
import RenderApi from './comps/render-api';
import AppPerm from './comps/app-perm';
import ApplyRecord from './comps/apply-record';
import McpServer from './comps/mcp-server.vue';
import { mapState } from 'vuex';

export default {
  components: {
    AppPerm,
    ApplyRecord,
    RenderApi,
    McpServer,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      isLoading: true,
      linkMap: {
        gateway: this.GLOBAL.DOC.APIGW_QUICK_START,
        API: this.GLOBAL.DOC.APIGW_USER_API,
      },
      active: 'gatewayApi',
      comKey: -1,
      pageKey: -1,
      isPlugin: false,
      curAppId: '',
      createTokenCofig: {
        visible: false,
      },
      curStep: 1,
      nextBtnDisabled: true,
      nextBtnLoading: false,
      steps: [
        { title: this.$t('应用 ID 确认'), icon: 1 },
        { title: this.$t('令牌查看'), icon: 2 },
      ],
      tokenUrl: '',
      errorObject: null,
      createNewTokenTips: {
        allowHtml: true,
        content: this.$t('令牌（access_token）可用于调用用户态的云 API，有效期 180 天。'),
        html: `${this.$t('令牌（access_token）可用于调用用户态的云 API，有效期 180 天。')} <a target="_blank" href="${
          this.GLOBAL.DOC.ACCESS_TOKEN_USAGE_GUIDE
        }" style="color: #3a84ff">${this.$t('使用指引')}</a>`,
        placements: ['bottom-end'],
        theme: 'light',
        width: 260,
        extCls: 'create-token-tips-cls',
      },
    };
  },
  computed: {
    ...mapState(['localLanguage', 'userFeature', 'platformFeature']),
    createTokenTip() {
      return this.$t('请完整输入应用 ID（{code}）确认', { code: this.appCode });
    },
    displayPanels() {
      const panels = [
        { name: 'gatewayApi', label: this.$t('网关API') },
        { name: 'componentApi', label: this.$t('组件API'), show: this.platformFeature?.ESB_API },
        { name: 'mcpServer', label: this.$t('MCP Server'), show: this.userFeature?.MCP_SERVER_API },
        { name: 'appPerm', label: this.$t('已申请的权限') },
        { name: 'applyRecord', label: this.$t('申请记录') },
      ];
      return panels.filter((panel) => panel.show === undefined || !!panel.show);
    },
    typeList() {
      const types = [
        { id: 'gateway', name: this.$t('网关API') },
        { id: 'component', name: this.$t('组件API'), visible: this.platformFeature?.ESB_API },
        { id: 'mcp', name: this.$t('MCP Server'), visible: this.userFeature?.MCP_SERVER_API },
      ];
      return types.filter((type) => type.visible !== false);
    },
    activeComponent() {
      const componentMap = {
        gatewayApi: 'RenderApi',
        mcpServer: 'McpServer',
        componentApi: 'RenderApi',
        appPerm: 'AppPerm',
        applyRecord: 'ApplyRecord',
      };
      return componentMap[this.active];
    },
    apiType() {
      const typeMap = {
        gatewayApi: 'gateway',
        mcpServer: 'mcp',
        componentApi: 'component',
      };
      return typeMap[this.active] || 'gateway';
    },
  },
  watch: {
    $route() {
      this.active = 'gatewayApi';
      this.pageKey = +new Date();
      this.isLoading = true;
    },
    curAppId(newVlaue) {
      if (newVlaue === this.appCode) {
        this.nextBtnDisabled = false;
      } else {
        this.nextBtnDisabled = true;
      }
    },
  },
  created() {
    this.isPlugin = this.$route.meta && this.$route.meta.isGetAppInfo;
    const { tabActive } = this.$route.params;
    if (tabActive) {
      this.active = tabActive;
    }
  },
  methods: {
    toLink(type) {
      window.open(this.linkMap[type]);
    },

    handlerDataReady() {
      this.isLoading = false;
    },

    handleTabChange() {
      this.comKey = +new Date();
    },

    // 获取新令牌
    async getAccessToken() {
      try {
        const res = await this.$store.dispatch('cloudApi/getAccessToken', {
          appCode: this.appCode,
        });
        // message: 字段处理
        if (res?.access_token) {
          // 正常响应处理
          this.tokenUrl = res.access_token;
        } else {
          // 错误响应处理
          this.errorObject = this.formatErrorString(res.message);
        }
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        setTimeout(() => {
          this.nextBtnLoading = false;
        }, 200);
      }
    },

    // 错误信息转换处理
    formatErrorString(message) {
      // 将错误字符串转换为一个格式正确的JSON字符串
      const jsonString = message
        .replace(/detail: /, '')
        .replace(/'/g, '"')
        .replace(/None/g, 'null')
        .replace(/False/g, 'false')
        .replace(/True/g, 'true');

      // 使用正则表达式来匹配JSON串
      const regex = /\{.*\}/;
      const matched = jsonString.match(regex);

      // 若匹配成功，则提取并解析JSON
      if (matched) {
        const detailStr = matched[0];

        try {
          const detailObj = JSON.parse(detailStr);
          return detailObj;
        } catch (error) {
          console.error('JSON parsing error:', error);
        }
      } else {
        console.error('No detail object found');
      }
      return null;
    },

    handleShowDialogCreateToken() {
      this.createTokenCofig.visible = true;
    },

    // 下一步
    handleNext() {
      if (this.curAppId !== this.appCode) {
        return;
      }
      this.nextBtnLoading = true;
      this.curStep = 2;
      this.getAccessToken();
    },

    // 取消状态重置
    handleCancel() {
      this.createTokenCofig.visible = false;
      // 消除消失闪烁
      setTimeout(() => {
        this.nextBtnDisabled = true;
        this.nextBtnLoading = false;
        this.curAppId = '';
        this.tokenUrl = '';
        this.curStep = 1;
        this.errorObject = null;
      }, 300);
    },
  },
};
</script>

<style lang="scss" scoped>
.cloud-wrapper {
  .ps-top-bar {
    padding: 0px 24px;
  }
  /deep/ .bk-tab-section {
    padding: 16px 0 0 0;
    background: #fff;
    box-shadow: 0 2px 4px 0 #1919290d;
  }
}

.cloud-container {
  position: relative;
  background: #fff;
  margin-top: 16px;
  padding-top: 0px;
  .cloud-type-item {
    padding: 0 24px 24px 24px;
  }
  .cloud-class {
    padding-top: 16px;
  }
}
.overview-tit {
  display: flex;
  justify-content: space-between;
  padding: 0 30px;
}

.api-type-list {
  padding-top: 16px;
  overflow: hidden;
  border-bottom: solid 1px #e6e9ea;
}

.api-type-list a {
  width: 50%;
  height: 34px;
  line-height: 34px;
  text-align: center;
  font-size: 16px;
  color: #5d6075;
  float: left;
  border-bottom: solid 3px #fff;
  cursor: pointer;
}

.api-type-list a.active {
  border-bottom: solid 3px #3a84ff;
  color: #3a84ff;
}

.ps-top-bar.cloud-api-permission {
  box-shadow: 0 3px 4px 0 #0000000a;
}

.steps-wrapper {
  width: 370px;
  margin: 0 auto;
}

.header-wrapper {
  text-align: left;
  height: 28px;
  font-family: MicrosoftYaHei;
  font-size: 20px;
  color: #313238;
  line-height: 28px;
}

.create-dialog-wrapper {
  .bk-alert {
    margin-top: 26px;
    margin-bottom: 24px;
  }
  .title {
    font-size: 14px;
    color: #63656e;
    line-height: 22px;
    margin-bottom: 6px;
  }
  .access-token-url {
    padding: 0 10px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 40px;
    background: #e1ecff;
    border-radius: 2px;
    font-family: MicrosoftYaHei;
    font-size: 14px;
    color: #313238;
    line-height: 22px;

    &.error {
      background: #ffeded;
      color: #63656e;
      margin-top: 24px;
    }

    .copy {
      color: #3a84ff;
      cursor: pointer;
    }
  }
}
.footer-wrapper {
  text-align: right;
}
.tab-container-cls {
  position: relative;
  .gateway-guide {
    position: absolute;
    right: 0px;
    top: 10px;
    z-index: 99;
    i {
      font-size: 16px;
    }
  }
}

.cloud-api-permission.plugin-top-bar {
  height: 52px;
  background: #fff;
  box-shadow: 0 3px 4px 0 #0000000a;
  position: relative;
  padding: 0 24px;

  .header-title {
    margin: 0 !important;
  }
}

.guide-wrapper {
  .bk-button:hover {
    background: #e1ecff;
    color: #1768ef;
    border-color: #1768ef;
  }
}

.alert-wrapper {
  font-size: 12px;
  color: #63656e;
  i {
    transform: translateY(0px);
    font-size: 14px;
    &.error {
      color: #ea3636;
    }
    &.success {
      color: #2dcb56;
    }
  }
}
</style>
<style>
.create-token-tips-cls .tippy-content {
  font-size: 12px;
  color: #63656e;
}
</style>
