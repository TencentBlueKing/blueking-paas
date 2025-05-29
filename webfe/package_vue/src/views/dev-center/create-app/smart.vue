<template>
  <div
    class="smart-app"
    data-test-id="createSmart_content_appData"
  >
    <div v-bkloading="{ isLoading: isDataLoading, zIndex: 10 }">
      <div
        data-test-id="createSmart_btn_appUploader"
        class="card-style smart-upload"
      >
        <div class="top-title">
          <div class="title mb10">
            {{ $t('基本信息') }}
          </div>
          <a
            href="https://bk.tencent.com/s-mart"
            target="_blank"
            class="f12"
          >
            {{ $t('什么是 S-mart 应用？') }}
          </a>
        </div>
        <bk-form
          :label-width="100"
          :model="formData"
          ref="smartForm"
          ext-cls="create-samrt-form-cls"
        >
          <bk-form-item
            :required="true"
            :label="$t('S-mart 包')"
          >
            <!-- 选择文件 -->
            <template v-if="!packageData">
              <uploader
                :key="renderUploaderIndex"
                :action="uploadUrl"
                :validate-name="/^[a-zA-Z0-9-_. ]+$/"
                :with-credentials="true"
                :name="'package'"
                :max-size="maxPackageSize"
                :other-params="formData"
                :headers="uploadHeader"
                :on-upload-success="handleSuccess"
                :on-upload-error="handleError"
                @file-change="handleFileChange"
              >
                <p
                  slot="tip"
                  class="uploader-tip"
                  style="font-size: 12px"
                >
                  {{ $t('将文件拖到此处或') }}
                  <span style="color: #3a84ff">{{ $t('点击上传') }}</span>
                </p>
              </uploader>
              <p
                slot="tip"
                class="form-tip"
              >
                {{ $t('仅支持蓝鲸 S-mart 包，上传成功后即可部署应用。支持的文件格式包括 .tar、.tgz 和 .tar.gz。') }}
              </p>
            </template>
            <!-- 成功后展示 -->
            <section v-else>
              <SmartFilePreview :file="fileInfo" />
              <SmartInfo
                :data="packageData"
                @change-app="handleChangeApp"
              />
            </section>
          </bk-form-item>
          <template v-if="isShowTenant">
            <bk-form-item
              :required="true"
              :property="'tenant'"
              error-display-type="normal"
              :label="$t('租户模式')"
            >
              <bk-radio-group v-model="formData.app_tenant_mode">
                <bk-radio-button value="single">{{ $t('单租户') }}</bk-radio-button>
                <bk-radio-button value="global">{{ $t('全租户') }}</bk-radio-button>
              </bk-radio-group>
            </bk-form-item>
            <bk-form-item
              v-if="formData.app_tenant_mode === 'single'"
              :required="true"
              :label="$t('租户 ID')"
            >
              <bk-input
                class="form-input-width"
                :value="curUserInfo.tenantId"
                :disabled="true"
              ></bk-input>
            </bk-form-item>
          </template>
        </bk-form>
      </div>
      <!-- code 存在冲突时，不展示包的解析出的信息 -->
      <div v-if="packageData && !isCodeConflicted">
        <div
          class="bk-alert bk-alert-success mb20"
          data-test-id="createSmart_header_appUpload"
        >
          <i class="paasng-icon paasng-check-circle-shape" />
          <div class="bk-alert-content">
            <div class="bk-alert-title">
              {{ $t('源码包上传成功，以下为从 app_desc.yml 文件中解析出的信息') }}
            </div>
            <div class="bk-alert-description" />
          </div>
          <div class="bk-alert-close close-text">
            <bk-button
              class="f12"
              :text="true"
              @click="handleReUpload"
            >
              {{ $t('重新上传') }}
            </bk-button>
          </div>
        </div>
        <div
          v-for="(packageItem, key) of packageData.app_description.modules"
          :key="key"
          class="package-data-box card-style"
        >
          <p class="package-data-title">
            <span>{{ key }}</span>
            <span
              v-if="packageItem.is_default"
              class="paas-tag"
            >
              {{ $t('主模块') }}
            </span>
          </p>
          <div>
            <KeyValueRow>
              <template #key>{{ $t('开发语言') }}：</template>
              <template #value>{{ packageItem.language }}</template>
            </KeyValueRow>
            <KeyValueRow>
              <template #key>
                <span
                  v-bk-tooltips="{
                    content: $t('增强服务只可新增，不可删除（即使在配置文件中删除了某增强服务，在平台也会保留该服务）'),
                    width: 280,
                  }"
                  class="has-desc"
                >
                  {{ $t('增强服务') }}：
                </span>
              </template>
              <!-- 增强服务 -->
              <template #value>
                <ul
                  class="package-data-services"
                  data-test-id="createSmart_list_appName"
                  v-if="packageItem.services?.length"
                >
                  <li
                    v-for="(service, index) of packageItem.services"
                    :key="index"
                    :class="packageData.supported_services.includes(service.name) ? 'added' : 'not_supported'"
                    class="package-data-rel"
                    v-bk-tooltips="{
                      content: $t('平台不支持该增强服务'),
                      disabled: packageData.supported_services.includes(service.name),
                    }"
                  >
                    {{ service.name }}
                    <i
                      v-if="service.shared_from"
                      v-bk-tooltips="`${$t('共享自')}${service.shared_from}${$t('模块')}`"
                      class="paasng-icon paasng-info-circle info-icon"
                    />
                  </li>
                </ul>
                <span v-else>{{ $t('无') }}</span>
              </template>
            </KeyValueRow>
          </div>
        </div>
      </div>
    </div>
    <div
      v-if="isDataLoading"
      class="data-loading"
    >
      <img src="/static/images/create-app-loading.svg" />
      <p>{{ $t('应用创建中，请稍候') }}</p>
    </div>
    <div
      v-else
      class="action-box"
    >
      <bk-button
        theme="primary"
        size="large"
        style="font-size: 14px"
        type="submit"
        :disabled="!packageData || isConflict"
        @click="handleCommit"
      >
        {{ $t('确认并创建应用') }}
      </bk-button>
      <bk-button
        size="large"
        class="ml15"
        style="width: 105px; font-size: 14px"
        @click.prevent="back"
      >
        {{ $t('返回') }}
      </bk-button>
    </div>
  </div>
</template>

<script>
import uploader from '@/components/uploader';
import { mapGetters } from 'vuex';
import SmartFilePreview from './comps/smart-file-preview.vue';
import SmartInfo from './comps/smart-info.vue';
import KeyValueRow from '@/components/key-value-row';
export default {
  components: {
    uploader,
    SmartFilePreview,
    SmartInfo,
    KeyValueRow,
  },
  data() {
    return {
      isDataLoading: false,
      packageData: null,
      renderUploaderIndex: 0,
      fileInfo: {},
      formData: {
        app_tenant_mode: 'single',
      },
      modifiedAppData: null,
    };
  },
  computed: {
    ...mapGetters(['isShowTenant']),
    uploadHeader() {
      return {
        name: 'X-CSRFToken',
        value: this.GLOBAL.CSRFToken,
      };
    },
    uploadUrl() {
      return `${BACKEND_URL}/api/bkapps/s-mart/`;
    },
    maxPackageSize() {
      return Number(window.BK_MAX_PACKAGE_SIZE) || 500;
    },
    curUserInfo() {
      return this.$store.state.curUserInfo;
    },
    isConflict() {
      if (
        this.packageData &&
        this.packageData.app_description?.code === this.packageData.original_app_description?.code
      ) {
        return false;
      }
      return !this.modifiedAppData;
    },
    // original_app_description 与 app_description 如果不一致说明(code|name)冲突了 (如果code一致，后台回在code加上两位随机数)
    isCodeConflicted() {
      const { original_app_description, app_description } = this.packageData;
      const originalCode = original_app_description?.code;
      const appCode = app_description?.code;
      // 修改后
      if (this.modifiedAppData) {
        return originalCode !== appCode && originalCode === this.modifiedAppData?.code;
      }
      return originalCode !== appCode;
    },
  },
  methods: {
    handleSuccess(res) {
      this.packageData = res;
    },

    handleError() {
      this.packageData = null;
      this.modifiedAppData = null;
    },

    // 文件选择
    handleFileChange(e) {
      const file = e.target.files[0];
      this.fileInfo = {
        name: file.name,
        size: (file.size / (1024 * 1024)).toFixed(2),
      };
    },

    back() {
      this.$router.push({
        name: 'myApplications',
      });
    },

    handleReUpload() {
      this.packageData = null;
      this.modifiedAppData = null;
    },

    // 修改应用信息
    handleChangeApp(data) {
      this.modifiedAppData = { ...data };
    },

    async handleCommit() {
      this.isDataLoading = true;
      try {
        const { code, name } = this.packageData.app_description;
        const params = {
          ...(this.modifiedAppData ? this.modifiedAppData : { code, name }),
          app_tenant_mode: this.formData.app_tenant_mode,
        };
        await this.$store.dispatch('packages/createSmartApp', {
          params,
        });

        this.$bkMessage({
          theme: 'success',
          message: this.$t('应用创建成功'),
        });

        const objectKey = `SourceInitResult${Math.random().toString(36)}`;
        this.$router.push({
          name: 'createSmartAppSucc',
          params: {
            id: this.modifiedAppData?.code || code,
          },
          query: { objectKey },
        });
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isDataLoading = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.default-info {
  background-color: #f0f8ff;
  border: 1px solid #a3c5fd;
  margin-bottom: 20px;
  font-size: 12px;
}
.smart-app {
  width: 1200px;
  margin: auto;
  .uploader-tip {
    font-size: 12px;
    font-weight: 400;
    span {
      color: #3a84ff;
    }
  }
  .smart-upload {
    padding: 24px;
    margin-bottom: 16px;
    .top-title {
      display: flex;
      align-items: center;
      justify-content: space-between;
      .title {
        line-height: 21px;
        color: #313238;
        font-size: 14px;
        font-weight: 600;
      }
    }
    .create-samrt-form-cls {
      width: 750px;
    }
    .form-tip {
      margin-top: 4px;
      font-size: 12px;
    }
    /deep/ .config-upload-content,
    /deep/ .config-upload-file {
      height: 180px;
      padding: 0;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    // /deep/ .config-upload-content {
    //   height: 180px;
    //   padding: 0;
    //   display: flex;
    //   justify-content: center;
    // }
    // /deep/ .config-upload-file {
    //   height: 180px;
    //   display: flex;
    //   align-items: center;
    //   padding: 0;
    // }
  }
}

.action-box {
  padding: 20px;
  text-align: center;
}

.package-data-box {
  padding: 20px;
  margin-bottom: 16px;
  .paas-tag {
    display: inline-block;
    height: 22px;
    line-height: 22px;
    margin-left: 8px;
    font-size: 12px;
    font-weight: 400;
    padding: 0 8px;
    color: #4d4f56;
    border-radius: 2px;
    background: #f0f1f5;
  }
  .has-desc {
    position: relative;
    &::after {
      content: '';
      position: absolute;
      width: calc(100% - 14px);
      border-bottom: 1px dashed;
      left: 50%;
      transform: translateX(-62%);
      bottom: -1px;
    }
  }
}

.package-data-title {
  font-size: 14px;
  margin-bottom: 16px;
  font-weight: 700;
  color: #313238;
  line-height: 22px;
  .confirm-key {
    text-align: right;
  }
}

.package-data-desc {
  font-size: 12px;
  font-weight: 400;
  color: #979ba5;
}

.package-data-services {
  overflow: hidden;
  display: flex;
  gap: 8px;
  li {
    height: 22px;
    line-height: 22px;
    display: inline-block;
    background: #f0f1f5;
    border-radius: 2px;
    padding: 0 2px;
    border-radius: 2px;
    text-align: center;
    font-size: 12px;
    color: #63656e;
    padding: 0 10px;

    &.added {
      background: #e5f6ea;
      color: #3fc06d;
    }

    &.deleted {
      background: #f0f1f5;
      color: #c4c6cc;
    }

    &.not_modified {
      background: #fff2dd;
      color: #ff9c01;
    }

    &.not_supported {
      background: #f0f1f5;
      color: #c4c6cc;
    }
  }
}

.package-data-rel {
  position: relative;
}

.info-icon {
  position: absolute;
  top: 1px;
  left: 87px;
  color: #52525d;
}

.mt2 {
  margin-top: 2px;
}

.data-loading {
  margin: 24px 0 18px;
  line-height: 16px;
  color: #666;
  text-align: center;

  img {
    width: 45px;
    margin-bottom: -2px;
    margin-left: 8px;
  }

  p:nth-child(2) {
    margin-top: 16px;
    color: #313238;
    font-size: 16px;
    font-weight: bold;
  }
}

.bk-alert {
  background-color: #e5f6ea;
  padding: 5px 10px;
  border: none;

  .bk-alert-title {
    line-height: 22px;
    color: #63656e;
  }

  .paasng-icon {
    color: #3fc06d;
    margin-right: 5px;
    line-height: 22px;
    vertical-align: middle;
  }

  &-success {
    display: flex;
  }
}
</style>
