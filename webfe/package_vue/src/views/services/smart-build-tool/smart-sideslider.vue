<template>
  <bk-sideslider
    :is-show.sync="sidesliderVisible"
    :quick-close="true"
    :title="$t('构建 S-mart 包')"
    show-mask
    width="960"
    ext-cls="smart-sideslider-cls"
    @shown="shown"
    @hidden="hidden"
  >
    <div
      :class="['sideslider-content', { 'execution-details': isExecutionDetails }]"
      slot="content"
    >
      <!-- 执行详情 -->
      <SmartExecutionDetails
        v-if="isExecutionDetails"
        :stream-url="getStreamUrl()"
        :build-id="buildData?.build_id"
        :is-detail-view="isDetail"
        :log-data="logData"
        :row-data="rowData"
        :key="smartKey"
        @close-sideslider="close"
      />
      <template v-else>
        <bk-form
          :model="formData"
          :label-width="100"
          ref="formRef"
        >
          <bk-form-item
            :label="$t('仓库类型')"
            :property="'type'"
            :required="true"
          >
            <bk-radio-group v-model="formData.type">
              <bk-radio
                value="default"
                disabled
                v-bk-tooltips="$t('暂不支持该类型')"
              >
                {{ $t('从代码仓库克隆') }}
              </bk-radio>
              <bk-radio value="source">{{ $t('上传源码包') }}</bk-radio>
            </bk-radio-group>
          </bk-form-item>
          <bk-form-item
            v-if="formData.type === 'source'"
            label=""
            :property="'type'"
          >
            <template v-if="!packageData">
              <!-- 文件上传 -->
              <Uploader
                :action="uploadUrl"
                :validate-name="/^[a-zA-Z0-9-_. ]+$/"
                :with-credentials="true"
                :name="'package'"
                :max-size="500"
                :other-params="formData"
                :headers="uploadHeader"
                :on-upload-success="handleSuccess"
                :on-upload-error="handleError"
                @file-change="handleFileChange"
              >
                <p
                  slot="tip"
                  class="uploader-tip f12 mt10"
                >
                  {{ $t('将文件拖到此处或') }}
                  <span style="color: #3a84ff">{{ $t('点击上传') }}</span>
                </p>
                <div
                  slot="custom-error"
                  class="error-links"
                  slot-scope="{ file }"
                >
                  <a
                    class="f12"
                    target="_blank"
                    :href="GLOBAL.DOC.APP_DESC_DOC + '_cnative'"
                  >
                    {{ $t('应用描述文件') }}
                    <i class="paasng-icon paasng-jump-link" />
                  </a>
                </div>
              </Uploader>
              <p
                slot="tip"
                class="f12 mt-4"
              >
                {{ $t('支持的文件格式包括：.tgz 和 .tar.gz，并确保 app_desc.yaml 文件在根目录') }}
              </p>
            </template>
            <!-- 文件上传成功展示 -->
            <SmartFilePreview
              v-if="packageData"
              :file="fileInfo"
              :status="'success'"
              :status-text="'上传成功'"
              is-closable
              @close="handleClearFile"
            />
          </bk-form-item>
          <!-- 示例目录 -->
          <ExampleDirectory v-if="formData.type === 'source'" />
        </bk-form>
        <section class="footer-btns">
          <bk-button
            class="mr-8"
            ext-cls="btn-cls"
            theme="primary"
            :loading="buildLoading"
            :disabled="!packageData"
            @click="buildSmartPackage"
          >
            {{ $t('构建') }}
          </bk-button>
          <bk-button
            ext-cls="btn-cls"
            theme="default"
            @click="close"
          >
            {{ $t('取消') }}
          </bk-button>
        </section>
      </template>
    </div>
  </bk-sideslider>
</template>

<script>
import Uploader from '@/components/uploader';
import SmartExecutionDetails from './smart-execution-details.vue';
import ExampleDirectory from './comps/example-directory.vue';
import SmartFilePreview from '@/views/dev-center/create-app/comps/smart-file-preview.vue';

export default {
  name: 'SmartSideslider',
  components: {
    Uploader,
    SmartExecutionDetails,
    ExampleDirectory,
    SmartFilePreview,
  },
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    isDetail: {
      type: Boolean,
      default: false,
    },
    rowData: {
      type: Object,
      default: () => ({}),
    },
    // 历史日志数据
    logData: {
      type: [Array, String],
      default: () => [],
    },
  },
  data() {
    return {
      formData: {
        type: 'source',
      },
      packageData: null,
      fileInfo: {},
      // 是否是执行详情侧边栏
      isExecutionDetails: false,
      buildData: null,
      buildLoading: false,
      smartKey: Date.now(),
    };
  },
  computed: {
    sidesliderVisible: {
      get: function () {
        return this.show;
      },
      set: function (val) {
        this.$emit('update:show', val);
      },
    },
    uploadUrl() {
      return `${BACKEND_URL}/api/tools/s-mart/upload/`;
    },
    uploadHeader() {
      return {
        name: 'X-CSRFToken',
        value: this.GLOBAL.CSRFToken,
      };
    },
    // 当前行的日志 stream_url
    curRowStreamUrl() {
      return `/streams/${this.rowData.uuid}`;
    },
  },
  methods: {
    // 获取 stream URL，确保只有在有效时才返回
    getStreamUrl() {
      if (this.buildData && this.buildData.stream_url) {
        return this.buildData.stream_url;
      }
      // 只有在 pending 状态时才返回 streamUrl 建立 SSE 连接
      if (this.isDetail && this.rowData && this.rowData.uuid && this.rowData.status === 'pending') {
        return this.curRowStreamUrl;
      }
      return '';
    },
    close() {
      this.$emit('close-sideslider');
      this.packageData = null;
      this.sidesliderVisible = false;
    },
    shown() {
      this.isExecutionDetails = this.isDetail;
    },
    hidden() {
      if ((this.isExecutionDetails && !this.isDetail) || this.rowData.status === 'pending') {
        this.$emit('refresh-list');
      }
      this.smartKey = Date.now();
      this.packageData = null;
      this.buildData = null;
    },
    handleSuccess(res) {
      this.packageData = res;
      this.$bkMessage({
        theme: 'success',
        message: '文件上传成功',
      });
    },
    // 上传失败
    handleError() {
      this.packageData = null;
    },
    // 文件选择
    handleFileChange(e) {
      const file = e.target.files[0];
      this.fileInfo = {
        name: file.name,
        size: (file.size / (1024 * 1024)).toFixed(2),
      };
    },
    // 上传源码包
    async buildSmartPackage() {
      this.buildLoading = true;
      try {
        const ret = await this.$store.dispatch('tool/smartBuild', {
          data: this.packageData,
        });
        this.buildData = ret;
        this.isExecutionDetails = true;
      } catch (err) {
        this.catchErrorHandler(err);
      } finally {
        this.buildLoading = false;
      }
    },
    // 清除已上传文件
    handleClearFile() {
      this.packageData = null;
      this.fileInfo = {};
    },
  },
};
</script>

<style lang="scss" scoped>
.smart-sideslider-cls {
  /deep/ .bk-sideslider-content {
    height: calc(100vh - 52px) !important;
  }
  .footer-btns {
    margin: 22px 0 0 100px;
  }
  .sideslider-content {
    height: 100%;
    padding: 16px 40px;
    &.execution-details {
      padding: 16px 24px 0;
    }
    .error-links {
      position: relative;
      z-index: 999;
    }
    .btn-cls {
      min-width: 88px;
    }
    /deep/ .config-upload-content,
    /deep/ .config-upload-file {
      min-height: 96px;
      padding: 12px 0;
      display: flex;
      align-items: center;
      justify-content: center;
      .content-icon {
        height: 28px;
        width: 28px;
        i {
          font-size: 28px;
        }
      }
    }
  }
}
</style>
