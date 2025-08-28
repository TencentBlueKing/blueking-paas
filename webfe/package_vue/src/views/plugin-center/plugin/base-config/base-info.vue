<template lang="html">
  <div class="right-main plugin-base-info">
    <paas-plugin-title />
    <paas-content-loader
      class="app-container pb-24"
      :is-loading="isLoading"
      placeholder="plugin-base-info-loading"
    >
      <section class="basic-info-container">
        <!-- Codecc 基本信息 -->
        <codecc-base-info v-if="isCodecc" />

        <!-- 基本信息 -->
        <plugin-base-info
          v-else
          :plugin-info="pluginInfo"
          @get-base-info="getPluginBaseInfo"
          @updata-log="handleUpdataLog"
        />

        <!-- 更多信息 -->
        <div
          class="basic-info-item mt16 card-style"
          v-if="isMoreInfo && !isCodecc"
        >
          <div class="title">
            {{ $t('更多信息') }}
            <span
              class="market-edit"
              @click="toMoreInfo"
            >
              <i class="paasng-icon paasng-edit-2" />
              {{ $t('编辑') }}
            </span>
          </div>
          <more-info
            ref="moreInfoRef"
            @show-info="isMoreInfo = $event"
            @set-schema="setPluginSchema"
          />
        </div>

        <!-- 市场信息 -->
        <plugin-market-info
          v-if="pluginFeatureFlags.MARKET_INFO"
          class="mt16"
          :market-info="marketInfo"
        />

        <!-- 插件使用方 -->
        <section
          v-if="pluginFeatureFlags.PLUGIN_DISTRIBUTER"
          class="plugin-users-info card-style mt16"
        >
          <p class="title">{{ $t('插件使用方') }}</p>
          <p class="description">{{ tipsInfo }}</p>
          <ul class="plugin-detail-wrapper">
            <li class="item-info">
              <div class="describe">
                {{ $t('蓝鲸网关') }}
              </div>
              <div class="right-content">
                <span
                  v-if="apiGwName"
                  style="color: #3a84ff"
                >
                  {{ $t('已绑定到') + apiGwName }}
                </span>
                <span
                  v-else
                  style="color: #979ba5"
                >
                  {{ $t('暂未找到已同步网关') }}
                </span>
                <i
                  v-bk-tooltips="$t('网关维护者默认为应用管理员')"
                  class="paasng-icon paasng-info-circle tooltip-icon ml5"
                />
              </div>
            </li>
            <li class="item-info">
              <div class="describe regular-stream">
                {{ $t('插件使用方') }}
              </div>
              <div class="plugin-users">
                <div>
                  <bk-transfer
                    :target-list="targetPluginList"
                    :source-list="pluginList"
                    :display-key="'name'"
                    :setting-key="'code_name'"
                    :show-overflow-tips="false"
                    :empty-content="promptContent"
                    :title="titleArr"
                    @change="transferChange"
                  />
                </div>
                <div class="mt20">
                  <bk-button
                    :theme="'primary'"
                    type="submit"
                    :title="$t('保存')"
                    class="mr10"
                    @click="updateAuthorizationUse"
                  >
                    {{ $t('保存') }}
                  </bk-button>
                  <bk-button
                    :theme="'default'"
                    :title="$t('还原')"
                    class="mr10"
                    @click="revivification"
                  >
                    {{ $t('还原') }}
                  </bk-button>
                </div>
                <div class="explain">
                  <p>
                    {{
                      $t(
                        '说明: 只有授权给了某个使用方，后者才能拉取到本地插件的相关信息，并在产品中通过访问插件注册到蓝鲸网关的API来使用插件功能。'
                      )
                    }}
                  </p>
                  <p>{{ $t('除了创建时注明的“插件使用方”之外，插件默认不授权给任何其他使用方。') }}</p>
                </div>
              </div>
            </li>
          </ul>
        </section>

        <!-- 鉴权信息 -->
        <authentication-info v-if="pluginFeatureFlags.APP_SECRETS" />

        <!-- 发布者 -->
        <publisher-info
          v-if="pluginFeatureFlags.PUBLISHER_INFO"
          class="mt16"
        />

        <!-- archivedStatus为 true && can_reactivate 为 true 展示上架 -->
        <div
          class="plugin-operation-wrapper"
          v-if="isArchivedStatus && offlineStatus"
        >
          <bk-button
            theme="primary"
            @click="handleShowPublishPopup"
          >
            {{ $t('上架插件') }}
          </bk-button>
          <i class="paasng-icon paasng-paas-remind-fill"></i>
          <div class="info">
            {{ $t('插件上架后，可在插件市场重新查看该插件的信息') }}
          </div>
        </div>

        <!-- archivedStatus为 true && can_reactivate 为 false 下架操作禁止用 -->
        <div
          class="plugin-operation-wrapper"
          v-else
        >
          <bk-button
            theme="danger"
            :disabled="isArchivedStatus && !offlineStatus"
            @click="showRemovePlugin"
          >
            {{ $t('下架插件') }}
          </bk-button>
          <i class="paasng-icon paasng-paas-remind-fill"></i>
          <span
            v-if="isArchivedStatus && !offlineStatus"
            class="offline-tip"
          >
            {{ $t('插件已下架') }}
          </span>
          <div class="info">
            {{ $t('插件下架后，插件市场不再展示该插件信息') }}
          </div>
        </div>
      </section>
    </paas-content-loader>

    <bk-dialog
      v-model="delPluginDialog.visiable"
      width="540"
      :title="$t(`确认下架插件【{id}】？`, { id: pluginInfo.id })"
      :theme="'primary'"
      :header-position="'left'"
      :mask-close="false"
      @after-leave="hookAfterClose"
    >
      <div class="ps-form">
        <div class="spacing-x1">
          {{ $t('请完整输入') }}
          <code>{{ pluginInfo.id }}</code>
          {{ $t('来确认下架插件！') }}
        </div>
        <div class="ps-form-group">
          <input
            v-model="formRemovePluginId"
            type="text"
            class="ps-form-control"
          />
          <div class="mt10 f13">
            {{ $t('注意：插件ID和名称在下架后') }}
            <strong>{{ $t('不会被释放') }}</strong>
            ，{{ $t('不能继续创建同名插件。') }}
          </div>
        </div>
      </div>
      <template slot="footer">
        <bk-button
          theme="primary"
          :loading="delPluginDialog.isLoading"
          :disabled="!formRemoveValidated"
          @click="confirmRemoval"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button
          theme="default"
          class="ml10"
          @click="delPluginDialog.visiable = false"
        >
          {{ $t('取消') }}
        </bk-button>
      </template>
    </bk-dialog>
  </div>
</template>

<script>
import pluginBaseMixin from '@/mixins/plugin-base-mixin';
import paasPluginTitle from '@/components/pass-plugin-title';
import authenticationInfo from '@/components/authentication-info.vue';
import MoreInfo from './comps/more-info.vue';
import pluginBaseInfo from './comps/base-info-item.vue';
import pluginMarketInfo from './comps/market-info-item.vue';
import publisherInfo from './comps/publisher-info.vue';
import codeccBaseInfo from './comps/codecc-base-info.vue';
// import 'BKSelectMinCss';
export default {
  components: {
    authenticationInfo,
    paasPluginTitle,
    MoreInfo,
    pluginBaseInfo,
    pluginMarketInfo,
    publisherInfo,
    codeccBaseInfo,
  },
  mixins: [pluginBaseMixin],
  data() {
    return {
      // 插件开发
      isLoading: true,
      isFormEdited: {
        nameInput: false,
        dataVolumeInput: false,
        classifyInput: false,
        profileInput: false,
        descriptionInput: false,
        contactsInput: false,
      },
      // 当前显示数据
      pluginInfo: {},
      // 服务器返回数据
      resPluginInfo: {
        pd_name: '',
      },
      marketInfo: {
        contactArr: [],
      },
      // 市场信息只读
      formRemovePluginId: '',
      delPluginDialog: {
        visiable: false,
        isLoading: false,
      },
      titleArr: [this.$t('可选的插件使用方'), this.$t('已授权给以下使用方')],
      promptContent: [this.$t('无数据'), this.$t('未选择已授权使用方')],
      apiGwName: '',
      TargetDataFirst: true,
      PluginDataAllFirst: true,
      targetPluginList: [],
      AuthorizedUseList: [],
      restoringPluginList: [],
      restoringTargetData: [],
      pluginList: [],
      tipsInfo: this.$t(
        '如果你将插件授权给某个使用方，对方便能读取到你的插件的基本信息、（通过 API 网关）调用插件的 API、并将插件能力集成到自己的系统中。'
      ),
      // 插件更多信息数据
      pluginSchema: {},
      isMoreInfo: true,
    };
  },
  computed: {
    // 下架插件输入id是否一致
    formRemoveValidated() {
      return this.pluginInfo.id === this.formRemovePluginId;
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    isArchivedStatus() {
      return this.curPluginInfo.status === 'archived';
    },
    offlineStatus() {
      return this.curPluginInfo.can_reactivate;
    },
    isCodecc() {
      return this.curPluginInfo.has_test_version;
    },
  },
  async created() {
    await this.init();
    this.refreshMoreInfo();
  },
  methods: {
    async init() {
      const ininRequest = [this.getMarketInfo(), this.getPluginBaseInfo()];
      await Promise.all(ininRequest);
      if (this.pluginFeatureFlags.PLUGIN_DISTRIBUTER) {
        this.getPluginAll();
        this.getAuthorizedUse();
        this.getProfile();
      }
      if (this.pluginFeatureFlags.APP_SECRETS) {
        await this.$store.dispatch('plugin/getPluginAppInfo', { pluginId: this.pluginId, pdId: this.pdId });
      }
      this.isLoading = false;
    },

    formattParams() {
      const data = {
        pdId: this.pdId,
        pluginId: this.pluginId,
      };
      return data;
    },

    // 基本信息
    async getPluginBaseInfo() {
      const data = this.formattParams();
      try {
        const res = await this.$store.dispatch('plugin/getPluginBaseInfo', data);
        this.pluginInfo = res;
        // 取消的还原数据
        this.resPluginInfo.name_zh_cn = res.name_zh_cn;
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 市场信息
    async getMarketInfo() {
      const data = this.formattParams();
      try {
        const res = await this.$store.dispatch('plugin/getMarketInfo', data);
        this.marketInfo = res;
        const contactformat = !res.contact ? [] : res.contact.split(',');
        this.$set(this.marketInfo, 'contactArr', contactformat);
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    /**
     * 选择文件后回调处理
     * @param {Object} e 事件
     */
    async handlerUploadFile(e) {
      e.preventDefault();
      const { files } = e.target;
      const data = new FormData();
      const fileInfo = files[0];
      const maxSize = 2 * 1024;
      // 支持jpg、png等图片格式，图片尺寸为72*72px，不大于2MB。验证
      const imgSize = fileInfo.size / 1024;

      if (imgSize > maxSize) {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('文件大小应<2M！'),
        });
        return;
      }

      data.append('logo', files[0]);
      const params = {
        pdId: this.pdId,
        pluginId: this.pluginId,
        data,
      };

      try {
        await this.$store.dispatch('plugin/uploadPluginLogo', params);
        this.$emit('current-plugin-info-updated');
        this.$paasMessage({
          theme: 'success',
          message: this.$t('logo上传成功！'),
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message,
        });
      }
    },

    handleUpdataLog() {
      this.$emit('current-plugin-info-updated');
    },

    showRemovePlugin() {
      this.delPluginDialog.visiable = true;
    },

    hookAfterClose() {
      this.delPluginDialog.visiable = false;
      this.formRemovePluginId = '';
    },

    async confirmRemoval() {
      this.delPluginDialog.isLoading = true;
      try {
        await this.$store.dispatch('plugin/offShelfPlugin', {
          pdId: this.pdId,
          pluginId: this.pluginId,
          data: {},
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('插件下架成功！'),
        });
        this.hookAfterClose();
        this.$router.push({
          name: 'plugin',
        });
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.delPluginDialog.isLoading = false;
      }
    },

    // 更多信息编辑
    toMoreInfo() {
      localStorage.setItem('pluginSchema', JSON.stringify(this.pluginSchema));
      this.$router.push({
        name: 'moreInfoEdit',
        params: {
          schema: this.pluginSchema,
        },
      });
    },

    // 获取可选插件适用方
    async getPluginAll() {
      try {
        const res = await this.$store.dispatch('plugin/getPluginDistributors');
        this.pluginList = res;
        if (this.PluginDataAllFirst) {
          this.restoringPluginList = this.pluginList;
          this.PluginDataAllFirst = false;
        }
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message || e.detail || this.$t('接口异常'),
        });
      }
    },

    arrayEqual(arr1, arr2) {
      if (arr1 === arr2) return true;
      if (arr1.length !== arr2.length) return false;
      for (let i = 0; i < arr1.length; ++i) {
        if (arr1[i] !== arr2[i]) return false;
      }
      return true;
    },

    async getProfile() {
      try {
        const res = await this.$store.dispatch('plugin/getProfileData', { pluginId: this.pluginId });
        this.apiGwName = res.api_gw_name;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message || e.detail || this.$t('接口异常'),
        });
      }
    },

    async updateAuthorizationUse() {
      const data = this.AuthorizedUseList;
      const flag = this.arrayEqual(this.targetPluginList, data);
      if (!flag) {
        try {
          await this.$store.dispatch('plugin/updatePluginUser', {
            pluginId: this.pluginId,
            data: { distributors: data },
          });
          this.getPluginAll();
          this.getAuthorizedUse();
          this.$paasMessage({
            theme: 'success',
            message: this.$t('授权成功！'),
          });
        } catch (e) {
          this.$paasMessage({
            theme: 'error',
            message: e.detail || e.message || this.$t('接口异常'),
          });
        }
      } else {
        this.$paasMessage({
          theme: 'warning',
          message: this.$t('未选择授权使用方'),
        });
      }
    },

    async getAuthorizedUse() {
      try {
        const res = await this.$store.dispatch('plugin/getAuthorizedUse', { pluginId: this.pluginId });
        this.targetPluginList = res.map((item) => item.code_name);
        if (this.TargetDataFirst) {
          this.restoringTargetData = this.targetPluginList;
          this.TargetDataFirst = false;
        }
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message || e.detail || this.$t('接口异常'),
        });
      }
    },

    transferChange(sourceList, targetList, targetValueList) {
      this.AuthorizedUseList = targetValueList;
    },

    revivification() {
      this.pluginList.splice(0, this.pluginList.length, ...this.restoringPluginList);
      this.targetPluginList.splice(0, this.targetPluginList.length, ...this.restoringTargetData);
    },

    // 设置插件 schema
    setPluginSchema(data) {
      this.pluginSchema = data;
    },

    // 刷新更多信息数据
    refreshMoreInfo() {
      this.$refs.moreInfoRef?.fetchPluginTypeList();
    },

    // 上架插件操作
    handleShowPublishPopup() {
      this.$bkInfo({
        confirmLoading: true,
        title: `${this.$t('确认上架插件')} ${this.pluginInfo.id}`,
        subTitle: `${this.$t('插件上架后，可在插件市场重新查看该插件')}`,
        confirmFn: async () => {
          try {
            await this.$store.dispatch('plugin/publishPlugin', {
              pluginId: this.pluginId,
            });
            this.$paasMessage({
              theme: 'success',
              message: this.$t('上架成功！'),
            });
            // 获取当前插件基本信息
            await this.$store.dispatch('plugin/getPluginInfo', { pluginId: this.pluginId, pluginTypeId: this.pdId });
            return true;
          } catch (e) {
            this.$paasMessage({
              theme: 'error',
              message: e.detail || e.message || this.$t('接口异常'),
            });
            return false;
          }
        },
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.mt16 {
  margin-top: 16px;
}
.basic-info-item {
  padding: 24px;
  .title {
    color: #313238;
    font-size: 14px;
    font-weight: bold;
    line-height: 1;
    margin-bottom: 5px;
  }
  .info {
    color: #979ba5;
    font-size: 12px;
  }
  .content {
    margin-top: 20px;
    border: 1px solid #dcdee5;
    border-radius: 2px;
    .input-show-index {
      z-index: 10;
    }
    .item-content {
      font-size: 12px;
      padding: 0 10px 0 25px;
      height: 42px;
      line-height: 42px;
      border-right: 1px solid #dcdee5;
      border-bottom: 1px solid #dcdee5;
    }

    .first-item-content {
      border-top: 1px solid #dcdee5;
    }

    .item-logn-content {
      padding: 20px 10px 0 25px;
      height: 105px;
      border-right: 1px solid #dcdee5;
      border-top: 1px solid #dcdee5;
      .tip {
        font-size: 12px;
        color: #979ba5;
      }
    }
    .title-label {
      font-size: 12px;
      display: inline-block;
      width: 180px;
      height: 42px;
      line-height: 42px;
      text-align: center;
      border: 1px solid #dcdee5;
      background: #fafbfd;
    }

    .plugin-info {
      height: 460px;
      padding-top: 20px;
    }
    .pre-release-wrapper,
    .production-wrapper {
      display: inline-block;
      position: relative;
      width: 430px;
      border: 1px solid #dcdee5;
      border-radius: 2px;
      vertical-align: top;
      &.has-left {
        left: 12px;
      }
      .header {
        height: 41px;
        line-height: 41px;
        border-bottom: 1px solid #dcdee5;
        background: #fafbfd;
        .header-title {
          margin-left: 20px;
          color: #63656e;
          font-weight: bold;
          float: left;
        }
        .switcher-wrapper {
          margin-right: 20px;
          float: right;
          .date-tip {
            margin-right: 5px;
            line-height: 1;
            color: #979ba5;
            font-size: 12px;
          }
        }
      }
      .ip-content {
        padding: 14px 24px 14px 14px;
        height: 138px;
        overflow-x: hidden;
        overflow-y: auto;
        .ip-item {
          display: inline-block;
          margin-left: 10px;
          vertical-align: middle;
        }
        .no-ip {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          text-align: center;
          font-size: 12px;
          color: #63656e;
          p:nth-child(2) {
            margin-top: 2px;
          }
        }
      }
    }
  }
}

.user-select-wrapper {
  .user-mask-layer {
    position: absolute;
    top: 0;
    z-index: 99;
    background: transparent;
    height: 41px;
    line-height: 41px;
    width: 100%;
    border: 1px solid #dcdee5;
  }
}
.market-edit,
.plugin-name-icon-cls {
  cursor: pointer;
  font-size: 14px;
  font-weight: 400;
  margin-left: 5px;
  color: #3a84ff;

  i {
    font-size: 16px;
    transform: translateX(2px);
  }
}
.explain {
  margin-top: 20px;
  p {
    line-height: 1.5em;
    color: #979ba5;
  }
}
.offline-tip {
  font-size: 12px;
  color: #979ba5;
  margin-left: 10px;
}
.plugin-users-info {
  padding: 24px;
  .title {
    font-weight: 700;
    font-size: 14px;
    color: #313238;
    line-height: 22px;
  }
  .description {
    margin-top: 4px;
    margin-bottom: 8px;
    font-size: 12px;
    color: #979ba5;
    line-height: 20px;
  }
  .plugin-detail-wrapper {
    border: 1px solid #dcdee5;
    .item-info {
      display: flex;
      min-height: 42px;
      border-top: 1px solid #dcdee5;
      &:first-child {
        border-top: none;
      }
      .describe,
      .right-content {
        display: flex;
        align-items: center;
        font-size: 12px;
      }
      .describe {
        flex-shrink: 0;
        justify-content: center;
        width: 180px;
        color: #313238;
        line-height: normal;
        background: #fafbfd;

        &.regular-stream {
          display: block;
          padding-top: 16px;
          text-align: center;
        }
      }
      .plugin-users {
        width: 100%;
        padding: 16px;
        border-left: 1px solid #dcdee5;
        &.no-padding-lf {
          padding-left: 0;
        }
      }
      .right-content {
        flex-wrap: wrap;
        line-height: 1.5;
        word-break: break-all;
        flex: 1;
        color: #63656e;
        padding-left: 16px;
        border-left: 1px solid #dcdee5;
      }
    }
  }
}

.plugin-operation-wrapper {
  display: flex;
  align-items: center;
  margin-top: 24px;
  font-size: 12px;
  color: #63656e;

  i {
    margin: 0 5px 0 16px;
    font-size: 14px;
    color: #ff9c01;
  }
}
</style>
<style lang="scss">
.content .paas-info-app-name-cls .bk-form-input {
  font-size: 12px !important;
}
.right-main {
  .cls-bk-input {
    input {
      padding-right: 85px !important;
      white-space: nowrap;
      text-overflow: ellipsis;
      overflow: hidden;
    }
  }
  .basic-info-item .content .editor-label {
    height: 232px;
    line-height: 232px;
    border-right-color: transparent;
  }
  .user-select-wrapper .bk-form-content .bk-tag-input {
    position: relative;
    z-index: 9;
    height: 41px;
    padding-right: 85px;
    padding-left: 20px;
    border-radius: 0 2px 2px 0;
    .placeholder {
      line-height: 41px;
      padding-left: 16px;
    }
  }
  .user-select-wrapper .mask-layer .bk-form-content .bk-tag-input i {
    display: none;
  }
}
.introductory .paas-info-app-name-cls input {
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}
</style>
