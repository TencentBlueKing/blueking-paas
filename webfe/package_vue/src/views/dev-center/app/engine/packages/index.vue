<template lang="html">
  <div class="right-main">
    <app-top-bar
      :title="$t('包版本管理')"
      :can-create="canCreateModule"
      :cur-module="curAppModule"
      :module-list="isLesscodeApp ? curAppModuleList : ''"
    />
    <paas-content-loader
      :is-loading="isPageLoading"
      placeholder="packages-loading"
      :offset-top="30"
      class="app-container middle overview"
    >
      <div class="ps-table-bar mb15 mt15">
        <bk-button
          v-if="isSmartApp"
          theme="default"
          @click="handleUpload"
        >
          <i class="paasng-icon paasng-plus mr5" /> {{ $t('上传新版本') }}
        </bk-button>
        <div
          v-if="isLesscodeApp"
          class="info-wrapper"
        >
          <bk-alert
            type="info"
            :title="$t('该模块部署版本包由“蓝鲸可视化开发平台”提供')"
          />
          <a
            v-if="lessCodeFlag && curAppModule.source_origin === GLOBAL.APP_TYPES.LESSCODE_APP"
            :href="lessCodeData.address_in_lesscode || 'javascript:;'"
            :target="lessCodeData.address_in_lesscode ? '_blank' : ''"
            class="link"
            @click="handleLessCode"
          > {{ $t('点击前往') }} <i class="paasng-icon paasng-jump-link" /></a>
        </div>
        <!-- <div class="bk-alert bk-alert-info mb10" v-if="isLesscodeApp">
                    <i class="bk-icon icon-info"></i>
                    <div class="bk-alert-content">
                        <div class="bk-alert-title">该模块部署版本包由“蓝鲸可视化开发平台”提供</div>
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
        >
          <template slot-scope="props">
            <span>{{ props.row.package_name || '--' }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('文件大小')"
          sortable="custom"
          prop="package_size"
        >
          <template slot-scope="props">
            <span>{{ props.row.size || '--' }} MB</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('摘要')"
          :show-overflow-tooltip="false"
        >
          <template slot-scope="props">
            <span v-bk-tooltips="props.row.sha256_signature || '--'">{{ props.row.sha256_signature ? props.row.sha256_signature.substring(0, 8) : '--' }}</span>
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('上传人')">
          <template slot-scope="props">
            <span>{{ props.row.operator || '--' }}</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('上传时间')"
          sortable="custom"
          prop="updated"
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
        <div class="package-data-box mb20">
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
                <span class="confirm-value">{{ uploadDialogConf.package.app_description.code }}</span>
              </bk-col>
            </bk-row>
            <bk-row class="mb15">
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
                <span class="confirm-value">{{ uploadDialogConf.package.app_description.name }}</span>
              </bk-col>
            </bk-row>
          </bk-container>
        </div>

        <div
          v-for="(packageItem, key) of uploadDialogConf.package.app_description.modules"
          :key="key"
          class="package-data-box mb20"
        >
          <p class="package-data-title">
            {{ key }}<span v-if="packageItem.is_default"> ({{ $t('主') }}) </span>
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
          <ul class="package-data-services">
            <li
              v-for="(service, index) of packageItem.services"
              :key="index"
              :class="uploadDialogConf.package.supported_services.includes(service.name) ? 'added' : 'not_supported'"
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
      <div v-else>
        <uploader
          :key="renderUploaderIndex"
          :action="uploadUrl"
          :with-credentials="true"
          :name="'package'"
          :accept-tips="$t('仅支持蓝鲸 S-mart 包，可以从“蓝鲸 S-mart”获取，上传成功后即可进行应用部署 仅支持 .tar 或 .tar.gz 格式的文件')"
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

    export default {
        components: {
            appTopBar,
            uploader
        },
        mixins: [appBaseMixin],
        data () {
            return {
                isDataCommiting: false,
                isPageLoading: true,
                isDataLoading: true,
                renderUploaderIndex: 0,
                packageList: [],
                uploadDialogConf: {
                    isShow: false,
                    title: '',
                    package: null
                },
                pagination: {
                    current: 1,
                    count: 0,
                    limit: 10,
                    order_by: ''
                },
                lessCodeData: {},
                lessCodeFlag: true
            };
        },
        computed: {
            uploadHeader () {
                return {
                    name: 'X-CSRFToken',
                    value: this.GLOBAL.CSRFToken
                };
            },
            uploadUrl () {
                return `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/source_package/stash/`;
            }
        },
        watch: {
            '$route' () {
                this.isPageLoading = true;
                this.resetParams();
                this.getPackageList();
            },
            curModuleId () {
                this.getLessCode();
            }
        },
        created () {
            this.getPackageList();
            this.getLessCode();
        },
        methods: {
            async getPackageList (page) {
                this.isDataLoading = true;
                try {
                    const curPage = page || this.pagination.current;
                    const params = {
                        limit: this.pagination.limit,
                        offset: this.pagination.limit * (curPage - 1)
                    };

                    if (this.pagination.order_by) {
                        params.order_by = this.pagination.order_by;
                    }

                    const res = await this.$store.dispatch('packages/getAppPackageList', {
                        isLesscodeApp: this.isLesscodeApp,
                        appCode: this.appCode,
                        moduleId: this.curModuleId,
                        params: params
                    });

                    res.results.forEach(item => {
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

            async handleCommitPackage () {
                this.isDataCommiting = true;
                try {
                    await this.$store.dispatch('packages/commitPackage', {
                        appCode: this.appCode,
                        moduleId: this.curModuleId,
                        signature: this.uploadDialogConf.package.signature
                    });

                    this.pagination.current = 1;
                    this.getPackageList();
                    this.$bkMessage({
                        theme: 'success',
                        message: this.$t('上传新版本成功')
                    });
                    this.uploadDialogConf.isShow = false;
                } catch (e) {
                    this.$bkMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('接口异常')
                    });
                } finally {
                    this.isDataCommiting = false;
                }
            },

            handleCancelCommit () {
                this.uploadDialogConf.isShow = false;
            },

            limitChange (limit) {
                this.pagination.limit = limit;
                this.pagination.current = 1;
                this.getPackageList(this.pagination.current);
            },

            pageChange (newPage) {
                this.pagination.current = newPage;
                this.getPackageList(newPage);
            },

            sortChange (params) {
                if (params.order === 'descending') {
                    this.pagination.order_by = `-${params.prop}`;
                } else if (params.order === 'ascending') {
                    this.pagination.order_by = `${params.prop}`;
                } else {
                    this.pagination.order_by = '';
                }
                this.getPackageList();
            },

            handleUpload () {
                this.renderUploaderIndex++;
                this.uploadDialogConf.package = null;
                this.uploadDialogConf.isShow = true;
            },

            handleUploadCallback (res) {
                return !!(res && res.signature);
            },

            resetParams () {
                this.pagination.current = 1;
                this.pagination.limit = 10;
            },

            handleSuccess (res) {
                this.uploadDialogConf.package = res;
                this.uploadDialogConf.title = this.$t('版本包详情');
            },

            handleError () {
                this.uploadDialogConf.package = null;
                this.uploadDialogConf.title = '';
            },

            async getLessCode () {
                try {
                    const resp = await this.$store.dispatch('baseInfo/gitLessCodeAddress', {
                        appCode: this.appCode,
                        moduleName: this.curModuleId
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

            handleLessCode () {
                if (this.lessCodeData.address_in_lesscode) {
                    return;
                }
                this.$bkMessage({ theme: 'warning', message: this.$t(this.lessCodeData.tips), delay: 2000, dismissable: false });
            }
        }
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
</style>
