<template>
  <div
    class="smart-app"
    data-test-id="createSmart_content_appData"
  >
    <div v-if="packageData">
      <div
        class="bk-alert bk-alert-success mb20"
        data-test-id="createSmart_header_appUpload"
      >
        <i class="paasng-icon paasng-check-circle-shape" />
        <div class="bk-alert-content">
          <div class="bk-alert-title">
            {{ $t('源码包上传成功，以下为从app_desc.yml文件中解析出的信息') }}
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
        class="package-data-box mb20"
        data-test-id="createSmart_header_appBaseInfo"
      >
        <p class="package-data-title">
          {{ $t('基本信息') }}
        </p>
        <bk-container
          :col="12"
          :margin="0"
        >
          <bk-row class="mb15">
            <bk-col
              class="pr0 f14 "
              :span="2"
            >
              <span class="confirm-key"> {{ $t('应用ID：') }} </span>
            </bk-col>
            <bk-col
              class="pl0 f14"
              :span="8"
            >
              <span class="confirm-value">{{ packageData.app_description.code }}</span>
            </bk-col>
          </bk-row>
          <bk-row>
            <bk-col
              class="pr0 f14"
              :span="2"
            >
              <span class="confirm-key"> {{ $t('应用名称：') }} </span>
            </bk-col>
            <bk-col
              class="pl0 f14"
              :span="8"
            >
              <span class="confirm-value">{{ packageData.app_description.name }}</span>
            </bk-col>
          </bk-row>
        </bk-container>
      </div>

      <div
        v-for="(packageItem, key) of packageData.app_description.modules"
        :key="key"
        class="package-data-box mb20"
      >
        <p class="package-data-title">
          {{ key }}<span v-if="packageItem.is_default"> ({{ $t('主') }}) </span>
        </p>
        <bk-container
          :col="12"
          :margin="0"
          data-test-id="createSmart_container_appLanguage"
        >
          <bk-row class="mb15">
            <bk-col
              class="pr0 f14 "
              :span="2"
            >
              <span class="confirm-key"> {{ $t('开发语言：') }} </span>
            </bk-col>
            <bk-col
              class="pl0 f14"
              :span="8"
            >
              <span class="confirm-value">{{ packageItem.language }}</span>
            </bk-col>
          </bk-row>
          <bk-row class="mb15">
            <bk-col
              class="pr0 f14"
              :span="2"
            >
              <span class="confirm-key"> {{ $t('增强服务') }} </span>
            </bk-col>
            <bk-col
              class="f12 pr0 pl0 mt2"
              :span="10"
            >
              <span class="confirm-value"> {{ $t('增强服务只可新增，不可删除（即使在配置文件中删除了某增强服务，在平台也会保留该服务）') }} </span>
            </bk-col>
          </bk-row>
        </bk-container>
        <ul
          class="package-data-services"
          data-test-id="createSmart_list_appName"
        >
          <li
            v-for="(service, index) of packageItem.services"
            :key="index"
            :class="packageData.supported_services.includes(service.name) ? 'added' : 'not_supported'"
            class="package-data-rel"
          >
            {{ service.name }}
            <i
              v-if="service.shared_from"
              v-bk-tooltips="`${$t('共享自')}${service.shared_from}${$t('模块')}`"
              class="paasng-icon paasng-info-circle info-icon"
            />
          </li>
        </ul>
      </div>
    </div>
    <div
      v-else
      data-test-id="createSmart_btn_appUploader"
    >
      <uploader
        :key="renderUploaderIndex"
        :action="uploadUrl"
        :with-credentials="true"
        :name="'package'"
        :accept-tips="$t('仅支持蓝鲸 S-mart 包，可以从“蓝鲸 S-mart”获取，上传成功后即可进行应用部署 仅支持 .tar 或 .tar.gz 格式的文件')"
        :headers="uploadHeader"
        :on-upload-success="handleSuccess"
        :on-upload-error="handleError"
      >
        <a
          slot="upload-footer"
          href="https://bk.tencent.com/s-mart"
          target="_blank"
          class="f12"
        > {{ $t('什么是 S-mart 应用？') }} </a>
      </uploader>
    </div>
    <div
      v-if="isDataLoading"
      class="data-loading"
    >
      <img src="/static/images/create-app-loading.svg">
      <p> {{ $t('应用创建中，请稍候') }} </p>
    </div>
    <div
      v-else
      class="action-box"
    >
      <bk-button
        theme="primary"
        size="large"
        style="font-size: 14px;"
        type="submit"
        :disabled="!packageData"
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

<script>import uploader from '@/components/uploader';
export default {
  components: {
    uploader,
  },
  data() {
    return {
      isDataLoading: false,
      packageData: null,
      renderUploaderIndex: 0,
    };
  },
  computed: {
    uploadHeader() {
      return {
        name: 'X-CSRFToken',
        value: this.GLOBAL.CSRFToken,
      };
    },
    uploadUrl() {
      return `${BACKEND_URL}/api/bkapps/s-mart/`;
    },
  },
  methods: {
    handleSuccess(res) {
      this.packageData = res;
    },

    handleError() {
      this.packageData = null;
    },

    back() {
      this.$router.push({
        name: 'myApplications',
      });
    },

    handleReUpload() {
      this.packageData = null;
    },

    async handleCommit() {
      this.isDataLoading = true;
      try {
        await this.$store.dispatch('packages/createSmartApp', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });

        this.$bkMessage({
          theme: 'success',
          message: this.$t('应用创建成功'),
        });

        const objectKey = `SourceInitResult${Math.random().toString(36)}`;
        const appCode = this.packageData.app_description.code;
        this.$router.push({
          name: 'createSmartAppSucc',
          params: {
            id: appCode,
          },
          query: { objectKey },
        });

        // this.$router.push({
        //     name: 'appDeploy',
        //     params: {
        //         id: this.packageData.app_description.code
        //     }
        // })
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

    .default-info{
        background-color: #F0F8FF;
        border: 1px solid #A3C5FD;
        margin-bottom: 20px;
        font-size: 12px;
    }
    .smart-app {
        padding-top: 20px;
        width: 1200px;
        margin: auto;
    }

    .action-box {
        padding: 20px;
        text-align: center;
    }

    .package-data-box {
        padding: 20px;
        border: 1px solid #dcdee5;
        border-radius: 2px;
    }

    .package-data-title {
        font-size: 14px;
        font-weight: 500;
        color: #313238;
        margin-bottom: 12px;
    }

    .package-data-desc {
        font-size: 12px;
        font-weight: 400;
        color: #979ba5;
    }

    .package-data-services {
        overflow: hidden;
        margin-top: 10px;
        li {
            min-width: 100px;
            height: 24px;
            line-height: 24px;
            display: inline-block;
            background: #F0F1F5;
            border-radius: 2px;
            padding: 0 2px;
            border-radius: 2px;
            margin: 0 8px 8px 0;
            text-align: center;
            font-size: 12px;
            color: #63656E;
            padding: 0 10px;

            &.added {
                background: #E5F6EA;
                color: #3FC06D;
            }

            &.deleted {
                background: #F0F1F5;
                color: #C4C6CC;
            }

            &.not_modified {
                background: #FFF2DD;
                color: #FF9C01;
            }

            &.not_supported {
                background: #F0F1F5;
                color: #C4C6CC;
                position: relative;

                &::after {
                    content: "";
                    width: 80%;
                    height: 1px;
                    background: #CCC;
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                }
            }
        }
    }

    .package-data-rel{
        position: relative;
    }

    .info-icon{
        position: absolute;
        top: 1px;
        left: 87px;
        color: #52525d;
    }

    .mt2{
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
        background-color: #E5F6EA;
        padding: 5px 10px;
        border: none;

        .bk-alert-title {
            line-height: 22px;
            color: #63656E;
        }

        .paasng-icon {
            color: #3FC06D;
            margin-right: 5px;
            line-height: 22px;
            vertical-align: middle
        }

        &-success {
            display: flex;
        }
    }
</style>
