<template lang="html">
  <div :class="['right-main', { 'packages-wrapper': isCloudNativeApp }, { 'bottom-line': !isSmartApp }]">
    <app-top-bar
      v-if="!isCloudNativeApp"
      :title="$t('包版本管理')"
      :can-create="canCreateModule"
      :cur-module="curAppModule"
      :module-list="isLesscodeApp ? curAppModuleList : []"
    />
    <div
      class="title"
      v-else
    >
      {{ isSmartApp ? $t('包版本管理') : $t('源码信息') }}
    </div>
    <paas-content-loader
      :is-loading="isPageLoading"
      placeholder="packages-loading"
      :offset-top="30"
      :class="['middle overview', { 'app-container': !isCloudNativeApp }]"
    >
      <div class="ps-table-bar mb15 mt15">
        <bk-button
          v-if="isSmartApp"
          theme="default"
          @click="handleUpload"
        >
          <i class="paasng-icon paasng-plus mr5" />
          {{ $t('上传新版本') }}
        </bk-button>
        <div
          v-if="isLesscodeApp"
          class="info-wrapper"
        >
          <bk-alert
            type="info"
            :title="$t('该模块部署版本包由“蓝鲸运维开发平台”提供')"
          />
          <a
            v-if="lessCodeFlag && curAppModule.source_origin === GLOBAL.APP_TYPES.LESSCODE_APP"
            :href="lessCodeData.address_in_lesscode || 'javascript:;'"
            :target="lessCodeData.address_in_lesscode ? '_blank' : ''"
            class="link"
            @click="handleLessCode"
          >
            {{ $t('点击前往') }}
            <i class="paasng-icon paasng-jump-link" />
          </a>
        </div>
        <!-- <div class="bk-alert bk-alert-info mb10" v-if="isLesscodeApp">
                    <i class="bk-icon icon-info"></i>
                    <div class="bk-alert-content">
                        <div class="bk-alert-title">该模块部署版本包由“蓝鲸运维开发平台”提供</div>
                        <div class="bk-alert-description"></div>
                    </div>
                    <a :href="GLOBAL.LINK.LESSCODE_INDEX" target="_blank"> {{ $t('点击前往') }} <i class="paasng-icon paasng-jump-link"></i></a>
                </div> -->
      </div>
      <bk-table
        v-bkloading="{ isLoading: isDataLoading }"
        :data="packageList"
        :size="'small'"
        :pagination="pagination"
        :outer-border="!isCloudNativeApp"
        @page-change="pageChange"
        @page-limit-change="limitChange"
        @sort-change="sortChange"
      >
        <div slot="empty">
          <table-empty empty />
        </div>
        <bk-table-column
          :label="$t('版本')"
          :show-overflow-tooltip="true"
        >
          <template slot-scope="props">
            <span>{{ props.row.version || '--' }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('文件名')"
          :show-overflow-tooltip="true"
          :render-header="$renderHeader"
        >
          <template slot-scope="props">
            <span>{{ props.row.package_name || '--' }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('文件大小')"
          sortable="custom"
          prop="package_size"
          :render-header="$renderHeader"
        >
          <template slot-scope="props">
            <span>{{ props.row.size || '--' }} MB</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('摘要')"
          :show-overflow-tooltip="false"
          :render-header="$renderHeader"
        >
          <template slot-scope="props">
            <span v-bk-tooltips="props.row.sha256_signature || '--'">
              {{ props.row.sha256_signature ? props.row.sha256_signature.substring(0, 8) : '--' }}
            </span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('上传人')"
          :render-header="$renderHeader"
        >
          <template slot-scope="props">
            <span>{{ props.row.operator || '--' }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('上传时间')"
          sortable="custom"
          prop="updated"
          :render-header="$renderHeader"
        >
          <template slot-scope="props">
            <span>{{ props.row.updated || '--' }}</span>
          </template>
        </bk-table-column>
      </bk-table>
    </paas-content-loader>

    <bk-dialog
      v-model="uploadDialogConf.isShow"
      :title="uploadDialogConf.title"
      :header-position="'left'"
      :close-icon="false"
      :width="640"
    >
      <div v-if="uploadDialogConf.package">
        <bk-alert
          v-if="isAppCodeChanged || isAppNameChanged"
          class="mb15"
          type="warning"
          :title="$t('创建应用时，已修改 Smart 包中的应用信息，上传新版本将自动根据创建时的选择进行更新')"
        ></bk-alert>
        <div class="package-data-box mb20">
          <p class="package-data-title">{{ $t('基本信息') }}</p>
          <KeyValueRow>
            <template #key>{{ $t('应用 ID') }}：</template>
            <template #value>
              <span :class="{ 'has-change': isAppCodeChanged }">{{ appDescription.code }}</span>
              <i
                v-if="isAppCodeChanged"
                class="paasng-icon paasng-info-line ml5"
                v-bk-tooltips="$t('Smart 包中声明的应用 ID 为：{n}', { n: originalCode })"
              ></i>
            </template>
          </KeyValueRow>
          <KeyValueRow>
            <template #key>{{ $t('应用名称') }}：</template>
            <template #value>
              <span :class="{ 'has-change': isAppNameChanged }">{{ appDescription.name }}</span>
              <i
                v-if="isAppNameChanged"
                class="paasng-icon paasng-info-line ml5"
                v-bk-tooltips="$t('Smart 包中声明的应用名称为：{n}', { n: originalName })"
              ></i>
            </template>
          </KeyValueRow>
        </div>

        <div
          v-for="(packageItem, key) of uploadDialogConf.package.app_description.modules"
          :key="key"
          class="package-data-box mb20"
        >
          <p class="package-data-title">
            {{ key }}
            <span
              v-if="packageItem.is_default"
              class="paas-tag"
            >
              {{ $t('主模块') }}
            </span>
          </p>
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
            <template #value>
              <ul
                v-if="packageItem.services?.length"
                class="package-data-services"
              >
                <li
                  v-for="(service, index) of packageItem.services"
                  :key="index"
                  :class="
                    uploadDialogConf.package.supported_services.includes(service.name) ? 'added' : 'not_supported'
                  "
                  class="package-data-rel"
                  v-bk-tooltips="{
                    content: $t('平台不支持该增强服务'),
                    disabled: uploadDialogConf.package.supported_services.includes(service.name),
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
              <div v-else>{{ $t('无') }}</div>
            </template>
          </KeyValueRow>
        </div>
      </div>
      <div v-else>
        <uploader
          :key="renderUploaderIndex"
          :validate-name="fileReg"
          :action="uploadUrl"
          :max-size="maxPackageSize"
          :with-credentials="true"
          :name="'package'"
          :accept-tips="$t('仅支持蓝鲸 S-mart 包，上传成功后即可部署应用。支持的文件格式包括 .tar、.tgz 和 .tar.gz。')"
          :headers="uploadHeader"
          :on-upload-success="handleSuccess"
          :on-upload-error="handleError"
        />
      </div>
      <div slot="footer">
        <bk-button
          class="mr5"
          theme="primary"
          :disabled="!uploadDialogConf.package"
          :loading="isDataCommiting"
          @click="handleCommitPackage"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button
          theme="default"
          @click="handleCancelCommit"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
    </bk-dialog>
  </div>
</template>

<script>
import appBaseMixin from '@/mixins/app-base-mixin.js';
import appTopBar from '@/components/paas-app-bar';
import uploader from '@/components/uploader';
import KeyValueRow from '@/components/key-value-row';

export default {
  components: {
    appTopBar,
    uploader,
    KeyValueRow,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      isDataCommiting: false,
      isPageLoading: true,
      isDataLoading: true,
      renderUploaderIndex: 0,
      packageList: [],
      uploadDialogConf: {
        isShow: false,
        title: '',
        package: null,
      },
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
        order_by: '',
      },
      lessCodeData: {},
      lessCodeFlag: true,
      fileReg: /^[a-zA-Z0-9-_. ]+$/,
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
      return `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/source_package/stash/`;
    },
    isSmartApp() {
      return this.curAppInfo.application?.is_smart_app;
    },
    maxPackageSize() {
      return window.BK_MAX_PACKAGE_SIZE || 500;
    },
    appDescription() {
      return this.uploadDialogConf.package.app_description || {};
    },
    originalAppDescription() {
      return this.uploadDialogConf.package.original_app_description || {};
    },
    originalCode() {
      return this.originalAppDescription.code;
    },
    originalName() {
      return this.originalAppDescription.name;
    },
    isAppCodeChanged() {
      return this.originalCode !== this.appDescription.code;
    },
    isAppNameChanged() {
      return this.originalName !== this.appDescription.name;
    },
  },
  watch: {
    $route() {
      this.isPageLoading = true;
      this.resetParams();
      this.getPackageList();
    },
    curModuleId() {
      this.getLessCode();
    },
  },
  created() {
    // 云原生设置表格配置项
    if (this.isCloudNativeApp) {
      this.pagination.limit = 5;
      this.pagination.limitList = [5, 10, 15, 20];
    }
    this.getPackageList();
    this.getLessCode();
  },
  methods: {
    async getPackageList(page) {
      this.isDataLoading = true;
      try {
        const curPage = page || this.pagination.current;
        const params = {
          limit: this.pagination.limit,
          offset: this.pagination.limit * (curPage - 1),
        };

        if (this.pagination.order_by) {
          params.order_by = this.pagination.order_by;
        }

        const res = await this.$store.dispatch('packages/getAppPackageList', {
          isLesscodeApp: this.isLesscodeApp,
          appCode: this.appCode,
          moduleId: this.curModuleId,
          params,
        });

        res.results.forEach((item) => {
          item.size = (item.package_size / 1024 / 1024).toFixed(2);
        });
        this.packageList = res.results;
        this.pagination.count = res.count;
      } catch (e) {
        // this.$bkMessage({
        //     theme: 'error',
        //     message: e.detail || e.message || this.$t('接口异常')
        // })
      } finally {
        this.isPageLoading = false;
        this.isDataLoading = false;
      }
    },

    async handleCommitPackage() {
      this.isDataCommiting = true;
      try {
        await this.$store.dispatch('packages/commitPackage', {
          appCode: this.appCode,
          signature: this.uploadDialogConf.package.signature,
        });

        this.pagination.current = 1;
        this.getPackageList();
        this.$bkMessage({
          theme: 'success',
          message: this.$t('上传新版本成功'),
        });
        this.uploadDialogConf.isShow = false;
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isDataCommiting = false;
      }
    },

    handleCancelCommit() {
      this.uploadDialogConf.isShow = false;
    },

    limitChange(limit) {
      this.pagination.limit = limit;
      this.pagination.current = 1;
      this.getPackageList(this.pagination.current);
    },

    pageChange(newPage) {
      this.pagination.current = newPage;
      this.getPackageList(newPage);
    },

    sortChange(params) {
      if (params.order === 'descending') {
        this.pagination.order_by = `-${params.prop}`;
      } else if (params.order === 'ascending') {
        this.pagination.order_by = `${params.prop}`;
      } else {
        this.pagination.order_by = '';
      }
      this.getPackageList();
    },

    handleUpload() {
      // eslint-disable-next-line no-plusplus
      this.renderUploaderIndex++;
      this.uploadDialogConf.package = null;
      this.uploadDialogConf.isShow = true;
    },

    handleUploadCallback(res) {
      return !!(res && res.signature);
    },

    resetParams() {
      this.pagination.current = 1;
      this.pagination.limit = 10;
    },

    handleSuccess(res) {
      this.uploadDialogConf.package = res;
      this.uploadDialogConf.title = this.$t('版本包详情');
    },

    handleError() {
      this.uploadDialogConf.package = null;
      this.uploadDialogConf.title = '';
    },

    async getLessCode() {
      try {
        const resp = await this.$store.dispatch('baseInfo/gitLessCodeAddress', {
          appCode: this.appCode,
          moduleName: this.curModuleId,
        });
        if (resp.address_in_lesscode === '' && resp.tips === '') {
          this.lessCodeFlag = false;
        }
        this.lessCodeData = resp;
      } catch (errRes) {
        this.lessCodeFlag = false;
        console.error(errRes);
      }
    },

    handleLessCode() {
      if (this.lessCodeData.address_in_lesscode) {
        return;
      }
      this.$bkMessage({ theme: 'warning', message: this.$t(this.lessCodeData.tips), delay: 2000, dismissable: false });
    },
  },
};
</script>

<style lang="scss" scoped>
.ps-table-bar {
  .info-wrapper {
    position: relative;
    .link {
      position: absolute;
      font-size: 12px;
      right: 10px;
      top: 8px;
    }
  }
}
.package-data-title {
  font-size: 14px;
  font-weight: 700;
  color: #313238;
  margin-bottom: 14px;
  line-height: 22px;
}

.package-data-desc {
  font-size: 12px;
  font-weight: 400;
  color: #979ba5;
}

.package-data-box {
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
  .has-change {
    color: #e38b02;
  }
  .paasng-info-line {
    cursor: pointer;
    color: #979ba5;
    &:hover {
      color: #4d4f56;
    }
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

.package-data-services {
  overflow: hidden;
  margin-top: 10px;
  li {
    height: 22px;
    line-height: 22px;
    display: inline-block;
    background: #f0f1f5;
    border-radius: 2px;
    padding: 0 2px;
    border-radius: 2px;
    margin: 0 8px 8px 0;
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
.packages-wrapper {
  margin-bottom: 24px;
  &.bottom-line {
    border-bottom: 1px solid #eaebf0;
  }
  .title {
    font-weight: 700;
    font-size: 14px;
    color: #313238;
  }
}
</style>
