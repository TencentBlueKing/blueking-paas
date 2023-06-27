<template>
  <div class="port-config">
    <div
      class="content"
      style="position: relative;"
    >
      <bk-table
        v-bkloading="{ isLoading: isTableLoading }"
        class="ps-version-list"
        :data="entryList"
        :size="'small'"
        :span-method="handleSpanMethod"
      >
        <bk-table-column :label="$t('模块')">
          <template slot-scope="{ row }">
            <span
              v-bk-tooltips="row.version"
              :class="{ 'version-num': row.version }"
              style="cursor: pointer;"
              @click="handleDetail(row)"
            >{{ row.version || '--' }}</span>
          </template>
        </bk-table-column>
      </bk-table>
      <bk-button
        v-if="moduleEntryInfo.type === 1 && canUpdateSubDomain"
        class="toggle-type"
        :text="true"
        theme="primary"
        @click="visitDialog.visiable = true"
      >
        {{ $t('切换为子域名') }}
      </bk-button>

      <bk-dialog
        v-model="visitDialog.visiable"
        width="600"
        :title="visitDialog.title"
        :theme="'primary'"
        :header-position="'left'"
        :mask-close="false"
        :loading="isLoading"
        @confirm="handleConfirm"
        @cancel="visitDialog.visiable = false"
      >
        <div class="tl">
          <p> {{ $t('注意事项：') }} </p>
          <p> {{ $t('1、应用的主访问路径将会变为子域名方式') }} </p>
          <p> {{ $t('2、如果应用框架代码没有适配过独立域名访问方式，一些静态文件路径可能会出现问题') }} </p>
          <p> {{ $t('3、旧的子路径地址依然有效，可以正常访问') }} </p>
        </div>
      </bk-dialog>

      <bk-dialog
        width="600"
        :value="domainDialog.visiable"
        :title="domainDialog.title"
        :theme="'primary'"
        :header-position="'left'"
        :mask-close="false"
        @confirm="updateRootDomain"
        @cancel="domainDialog.visiable = false"
      >
        <div class="tl">
          <p> {{ $t('更改后：') }} </p>
          <p>1. {{ $t('该模块的默认访问地址的根域为变为：') }}{{ rootDomainDefault }}</p>
          <p>2. {{ $t('若该模块为主模块，则应用市场访问地址的根域也会变为：') }}{{ rootDomainDefault }}</p>
        </div>
      </bk-dialog>
    </div>
  </div>
</template>

<script>import appBaseMixin from '@/mixins/app-base-mixin';
export default {
  mixins: [appBaseMixin],
  data() {
    return {
      type: '',
      example: '',
      canUpdateSubDomain: false,
      isLoading: false,
      visitDialog: {
        visiable: false,
        title: this.$t('确认切换为子域名访问地址？'),
      },
      moduleEntryInfo: {
        entrances: [],
        type: 1,
        entrancesTemplate: {},
      },
      region: '',
      rootDomains: [],
      rootDomainDefault: '',
      isEdited: false,
      domainDialog: {
        visiable: false,
        title: this.$t('确认更改默认根域？'),
      },
      rootDomainDefaultDiff: '',
      isTableLoading: false,
      entryList: [],
    };
  },
  computed: {
    platformFeature() {
      return this.$store.state.platformFeature;
    },
  },
  watch: {
    '$route'() {
      this.init();
    },
  },
  created() {
    this.init();
  },
  methods: {
    /**
     * 数据初始化入口
     */
    init() {
      this.getAppRegion();
      this.getEntryInfo();
      this.getDefaultDomainInfo();
    },

    async getAppRegion() {
      this.canUpdateSubDomain = false;
      try {
        const { region } = this.curAppInfo.application;
        const res = await this.$store.dispatch('getAppRegion', region);
        this.canUpdateSubDomain = res.entrance_config.manually_upgrade_to_subdomain_allowed;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message || e.detail || this.$t('接口异常'),
        });
      } finally {
        this.$emit('data-ready', 'visit-config');
      }
    },

    async getEntryInfo() {
      try {
        const res = await this.$store.dispatch('entryConfig/getEntryInfo', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        this.moduleEntryInfo = res;
        this.moduleEntryInfo.entrancesTemplate = res.entrances.reduce((p, v) => {
          p[v.env].push(v);
          return p;
        }, { stag: [], prod: [] });
      } catch (e) {
        this.moduleEntryInfo = {
          entrances: [],
          type: 1,
          entrancesTemplate: {},
        };
        this.$paasMessage({
          theme: 'error',
          message: e.message || e.detail || this.$t('接口异常'),
        });
      }
    },

    async handleConfirm() {
      this.isLoading = true;
      try {
        await this.$store.dispatch('entryConfig/updateEntryType', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          type: 2,
        });
        this.$bkMessage({
          theme: 'success',
          message: this.$t('修改成功'),
        });
        this.$store.commit('updateCurAppModuleExposed', 2);
        this.visitDialog.visiable = false;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message || e.detail || this.$t('接口异常'),
        });
      } finally {
        this.isLoading = false;
      }
    },

    async getDefaultDomainInfo() {
      try {
        const res = await this.$store.dispatch('entryConfig/getDefaultDomainInfo', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        this.rootDomains = res.root_domains || [];
        this.rootDomainDefault = res.preferred_root_domain;
        this.rootDomainDefaultDiff = res.preferred_root_domain;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message || e.detail || this.$t('接口异常'),
        });
      }
    },

    async updateRootDomain() {
      try {
        await this.$store.dispatch('entryConfig/updateRootDomain', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          data: {
            preferred_root_domain: this.rootDomainDefault,
          },
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('修改成功'),
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message || e.detail || this.$t('接口异常'),
        });
      } finally {
        this.isEdited = false;
        this.domainDialog.visiable = false;
        this.getDefaultDomainInfo();
      }
    },

    showEdit() {
      this.isEdited = true;
    },

    handleShowDialog() {
      if (this.rootDomainDefaultDiff !== this.rootDomainDefault) {
        this.domainDialog.visiable = true;
      }
    },

    handleCancel() {
      this.isEdited = false;
      if (this.rootDomainDefaultDiff !== this.rootDomainDefault) {
        this.getDefaultDomainInfo();
      }
    },
  },
};
</script>

<style lang="scss" scoped>
    .toggle-type {
        position: absolute;
        right: 20px;
        top: 11px;
    }

    .root-domains-row {
        display: flex;
        justify-content: space-between;
    }

    .root-domains-wrapper {
        display: flex;
        .root-domain:nth-child(n + 2) {
            margin-left: 20px;
        }
    }

    .action-box {
        line-height: 40px;
        margin-right: 20px;
    }

    .root-url {
        font-size: 13px;
    }

    .td-focus {
        border: 1px solid #3a84ff;
        transition: all .1s;
        transform: translateY(-1px);
    }
    .td-title {
        width: 180px;
        text-align: center;
        padding: 0;
    }
</style>
