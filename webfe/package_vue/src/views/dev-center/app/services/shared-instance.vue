<template lang="html">
  <div class="right-main">
    <!-- 内容 -->
    <app-top-bar
      v-if="!isCloudNativeApp"
      :paths="servicePaths"
      :can-create="canCreateModule"
      :cur-module="curAppModule"
      :title="$t('数据存储')"
    />

    <div class="app-container shared-container">
      <paas-content-loader
        :is-loading="isLoading"
        placeholder="data-inner-shared-loading"
        :height="600"
        :offset-top="0"
        class="shared-detail-container"
      >
        <section class="detail-item">
          <h4> {{ $t('服务说明') }} </h4>
          <p> {{ $t('本服务共享自') }} {{ refModuleName }} {{ $t('模块的对应服务实例。') }} </p>
          <bk-button @click="handleViewDetail">
            {{ $t('查看原有实例详情') }}
          </bk-button>
        </section>
        <section class="detail-item mt20">
          <h4> {{ $t('解除共享') }} </h4>
          <p> {{ $t('解除共享关系后，当前模块将无法获取') }}
            {{ refModuleName }} {{ $t('模块的') }} {{ servieceName }} {{ $t('服务的所有环境变量。') }} </p>
          <bk-button @click="handleOpenRemoveDialog">
            {{ $t('解除服务共享') }}
          </bk-button>
        </section>
      </paas-content-loader>
    </div>

    <bk-dialog
      v-model="removeSharedDialog.visiable"
      width="540"
      :title="$t('确认解除服务共享')"
      :theme="'primary'"
      :mask-close="false"
      :loading="removeSharedDialog.isLoading"
      @after-leave="hookAfterClose"
    >
      <form
        class="ps-form"
        @submit.prevent="submitRemoveShared"
      >
        <div class="spacing-x1">
          {{ $t('请完整输入应用 ID ') }}<code>{{ appCode }}</code> {{ $t('确认：') }}
        </div>
        <div class="ps-form-group">
          <input
            v-model="formRemoveConfirmCode"
            type="text"
            class="ps-form-control"
          >
        </div>
        <bk-alert
          style="margin-top: 10px;"
          type="error"
          :title="errorTips"
        />
      </form>
      <template slot="footer">
        <bk-button
          theme="primary"
          :loading="removeSharedDialog.isLoading"
          :disabled="!formRemoveValidated"
          @click="submitRemoveShared"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button
          theme="default"
          @click="removeSharedDialog.visiable = false"
        >
          {{ $t('取消') }}
        </bk-button>
      </template>
    </bk-dialog>
  </div>
</template>

<script>import appBaseMixin from '@/mixins/app-base-mixin';
import appTopBar from '@/components/paas-app-bar';
import { bus } from '@/common/bus';

export default {
  components: {
    appTopBar,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      servicePaths: [],
      categoryId: 0,
      service: this.$route.params.service,
      requestQueue: ['init', 'detail'],
      detailData: {},
      removeSharedDialog: {
        visiable: false,
        isLoading: false,
      },
      formRemoveConfirmCode: '',
    };
  },
  computed: {
    isLoading() {
      return this.requestQueue.length > 0;
    },
    refModuleName() {
      return this.detailData.ref_module ? this.detailData.ref_module.name : '';
    },
    servieceName() {
      return this.detailData.service ? this.detailData.service.display_name : '';
    },
    formRemoveValidated() {
      return this.appCode === this.formRemoveConfirmCode;
    },
    errorTips() {
      return `${this.$t('解除后，当前模块将无法获取 ')}${this.refModuleName} ${this.$t('模块的')} ${this.servieceName} ${this.$t('服务的所有环境变量')}`;
    },
  },
  watch: {
    '$route'() {
      this.init();
      this.fetchData();
    },
  },
  created() {
    this.init();
    this.fetchData();
  },
  methods: {
    init() {
      this.$http.get(`${BACKEND_URL}/api/services/${this.service}/`).then((response) => {
        this.servicePaths = [];
        const resData = response.result;
        this.servicePaths.push({
          title: resData.category.name,
          routeName: 'appService',
        });
        this.servicePaths.push({
          title: this.curModuleId,
        });
        this.servicePaths.push({
          title: resData.display_name,
        });
        this.categoryId = resData.category.id;
      })
        .finally(() => {
          this.requestQueue.shift();
        });
    },

    handleViewDetail() {
      // 跳转至该服务的分享模块
      if (this.isCloudNativeApp && this.detailData.ref_module.name) {
        const routeConfig = {
          name: 'cloudAppServiceInner',
          params: {
            id: this.appCode,
            category_id: this.categoryId,
            service: this.service,
            // 分享模块名
            moduleId: this.detailData.ref_module.name,
          },
        };
        bus.$emit('cloud-change-module', routeConfig);
        return;
      }
      this.$router.push({
        name: this.isCloudNativeApp ? 'cloudAppServiceInner' : 'appServiceInner',
        params: {
          id: this.appCode,
          category_id: this.categoryId,
          service: this.service,
          moduleId: this.detailData.ref_module.name,
        },
      });
    },

    hookAfterClose() {
      this.formRemoveConfirmCode = '';
    },

    handleOpenRemoveDialog() {
      this.removeSharedDialog.visiable = true;
    },

    async submitRemoveShared() {
      this.removeSharedDialog.isLoading = true;
      try {
        await this.$store.dispatch('service/deleteSharedAttachment', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          serviceId: this.service,
        });
        this.removeSharedDialog.visiable = false;
        this.$paasMessage({
          theme: 'success',
          message: this.$t('解除服务共享成功'),
          delay: 1500,
        });
        this.$router.push({
          name: 'appService',
          params: {
            category_id: this.categoryId,
            id: this.appCode,
          },
        });
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.removeSharedDialog.isLoading = false;
      }
    },

    async fetchData() {
      try {
        const res = await this.$store.dispatch('service/getSharedAttachmentDetail', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          serviceId: this.service,
        });
        this.detailData = JSON.parse(JSON.stringify(res));
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.requestQueue.shift();
      }
    },
  },
};

</script>

<style lang="scss" scoped>
    .app-container {
        .detail-item {
            h4 {
                margin-bottom: 15px;
            }
            p {
                margin-bottom: 5px;
                line-height: 24px;
                font-size: 14px;
            }
        }
    }
    .shared-container{
        background: #fff;
        margin-top: 16px;
        min-height: 640px;
        .shared-detail-container{
            padding: 10px 24px 16px 24px;
        }
    }
</style>
