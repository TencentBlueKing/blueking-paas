<template>
  <div class="services-container">
    <paas-content-loader
      class="app-container image-content"
      :is-loading="isLoading"
      placeholder="roles-loading"
    >
      <div class="middle ps-main">
        <bk-table
          v-bkloading="{ isLoading: tableLoading, opacity: 1 }"
          :data="tableList"
          size="small"
          :pagination="pagination"
          @page-change="pageChange"
          @page-limit-change="limitChange"
          @row-mouse-enter="handleRowMouseEnter"
          @row-mouse-leave="handleRowMouseLeave"
        >
          <div slot="empty">
            <table-empty empty />
          </div>
          <bk-table-column :label="$t('服务名称')">
            <template slot-scope="{row, $index}">
              <div class="flex-row align-items-center">
                <img class="row-img mr10" :src="row.logo" alt="">
                <bk-button text>{{ row.name || '--' }}</bk-button>
                <router-link
                  v-if="$index === rowIndex"
                  target="_blank"
                  :to="{ name: 'serviceInnerPage',
                         params: { category_id: row.category ? row.category.id : '', name: row.name },
                         query: { name: row.display_name } }">
                  <i
                    class="row-icon paasng-icon paasng-page-fill pl5 mt5"
                    v-bk-tooltips="{content: '使用指南'}" />
                </router-link>
              </div>
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('预发布环境')">
            <template slot-scope="{row}">
              <span v-if="row.type === 'bound' && row.provision_infos && row.provision_infos.stag">
                <i
                  class="paasng-icon paasng-correct success-icon"
                />
              </span>
              <span v-else>--</span>
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('生产环境')">
            <template slot-scope="{row}">
              <span v-if="row.type === 'bound' && row.provision_infos && row.provision_infos.prod">
                <i
                  class="paasng-icon paasng-correct success-icon"
                />
              </span>
              <span v-else>--</span>
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('配置信息')">
            <template slot-scope="{row}">
              <span v-if="row.specifications && row.specifications.length">
                <bk-tag v-for="(item) in row.specifications" :key="item.recommended_value">
                  {{ $t(item.display_name) }} {{ $t(item.recommended_value) }}
                </bk-tag>
              </span>
              <span v-else>--</span>
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('共享信息')">
            <template slot-scope="{row}">
              <span v-if="row.type === 'bound' && row.ref_modules && row.ref_modules.length">
                {{ $t('被') }} {{ row.ref_modules.map(e => e.name).join(',') }} {{ $t('模块共享使用这个字段') }}
              </span>
              <span v-else-if="row.type === 'shared' && row.ref_modules && row.ref_modules.length">
                {{ $t('共享来自') }} {{ row.ref_modules.map(e => e.name).join(',') }} {{ $t('使用这个字段') }}
              </span>
              <span v-else>--</span>
            </template>
          </bk-table-column>
          <bk-table-column
            width="180"
            :label="$t('启/停')"
          >
            <template slot-scope="{row}">
              <div
                class="ps-switcher-wrapper"
                @click="toggleSwitch"
                v-if="row.isStartUp">
                <bk-switcher
                  v-model="row.isStartUp"
                  :theme="row.type === 'shared' ? 'success' : 'primary'"
                  class="bk-small-switcher"
                />
              </div>
              <div
                class="ps-switcher-wrapper"
                v-else
                @click="toggleSwitch(row)"
                v-bk-tooltips="switcherTips"
              >
                <bk-switcher
                  v-model="row.isStartUp"
                  class="bk-small-switcher"
                />
              </div>

              <div id="switcher-tooltip">
                <div v-for="item in startData" :key="item.id" class="item" @click="handleSwitcherOpen(item)">
                  {{ item.label }}
                </div>
              </div>
              <!-- <bk-dropdown-menu ref="dropdown" v-else>
                <div class="dropdown-trigger-text" slot="dropdown-trigger">

                </div>
                <ul class="bk-dropdown-list" slot="dropdown-content">
                  <li><a href="javascript:;">生产环境</a></li>
                  <li><a href="javascript:;">预发布环境</a></li>
                </ul>
              </bk-dropdown-menu> -->

            </template>
          </bk-table-column>
        </bk-table>
      </div>
      <shared-dialog
        :data="curData"
        :show.sync="isShowDialog"
        @on-success="handleExportSuccess"
      />

      <bk-dialog
        v-model="isShowStartDialog"
        width="480"
        :title="$t('配置信息')"
        :mask-close="false"
        ext-cls="paasng-service-export-dialog-cls"
        header-position="left"
        @confirm="handleConfigChange">
        <bk-form
          :model="startFormData">
          <bk-form-item
            v-for="(item, index) in definitions" :key="index"
            :label="item.display_name"
          >
            <!-- <span class="form-text">{{ artifactType || '--' }}</span> -->
            <bk-radio-group
              v-model="item.active"
            >
              <bk-radio
                v-for="childrenItem in item.children"
                :key="childrenItem"
                :value="childrenItem"
              >
                {{ childrenItem }}
              </bk-radio>
            </bk-radio-group>
          </bk-form-item>
        </bk-form>
      </bk-dialog>
    </paas-content-loader>
  </div>
</template>

<script>import appBaseMixin from '@/mixins/app-base-mixin';
import SharedDialog from './comps/shared-dialog';

export default {
  components: {
    SharedDialog,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      tableList: [],
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
      },
      tableLoading: false,
      isLoading: false,
      rowIndex: '',
      isShowDate: false,
      isShowStartDialog: false,
      switcherTips: {
        allowHtml: true,
        width: 140,
        trigger: 'click',
        theme: 'light',
        content: '#switcher-tooltip',
        placement: 'bottom',
        extCls: 'tips-cls',
      },
      startData: [{ value: 'start', label: this.$t('直接启用') }, { value: 'shared', label: this.$t('从其他模块共享') }],
      isShowDialog: false,
      curData: {},
      startFormData: {},
      definitions: [],
    };
  },
  computed: {
    appCode() {
      return this.$route.params.id;
    },
    curAppCode() {
      return this.$store.state.curAppCode;
    },
    region() {
      return this.curAppInfo.application.region;
    },
  },
  watch: {
    curAppCode() {
      this.gettableList();
      this.isLoading = true;
    },
  },
  created() {
    this.init();
  },
  methods: {
    init() {
      this.gettableList();
    },

    // 获取表格列表
    async gettableList() {
      this.tableLoading = true;
      try {
        const { appCode } = this;
        const res = await this.$store.dispatch('service/getServicesList', { appCode, moduleId: this.curModuleId });
        // 改造bound数据
        res.bound = (res.bound || []).reduce((p, v) => {
          p.push({ ...v, ...v.service, type: 'bound', isStartUp: true });
          return p;
        }, []);
        // 改造shared数据
        res.shared = (res.shared || []).map((e) => {
          e.type = 'shared';
          e.isStartUp = true;
          return e;
        });

        // 改造shared数据
        res.unbound = (res.unbound || []).map((e) => {
          e.type = 'unbound';
          e.isStartUp = false;
          return e;
        });
        this.tableList = [...res.bound, ...res.shared, ...res.unbound];
        console.log('this.tableList', this.tableList);
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || this.$t('接口异常'),
        });
      } finally {
        this.tableLoading = false;
        setTimeout(() => {
          this.isLoading = false;
        }, 500);
      }
    },
    pageChange(page) {
      if (this.currentBackup === page) {
        return;
      }
      this.pagination.current = page;
    },

    limitChange(currentLimit) {
      this.pagination.limit = currentLimit;
      this.pagination.current = 1;
    },

    // 表格鼠标移入
    handleRowMouseEnter(index) {
      this.rowIndex = index;
    },

    // 表格鼠标移出
    handleRowMouseLeave() {
      this.rowIndex = '';
    },

    toggleSwitch(payload) {
      console.log('payload', payload);
      this.curData = payload;
    },


    handleSwitcherOpen(payload) {
      if (payload.value === 'start') {  // 直接启动
        this.isShowStartDialog = true;
        this.fetchServicesSpecsDetail();
      } else {    // 从其他模块中共享
        this.isShowDialog = true;
      }
    },

    handleExportSuccess() {
      this.init();
    },


    // 获取启动时需要的配置信息
    async fetchServicesSpecsDetail() {
      try {
        console.log(this.region);
        const res = await this.$store.dispatch('service/getServicesSpecsDetail', {
          id: this.curData.uuid,
          region: this.region,
        });
        (res.definitions || []).forEach((item, index) => {
          let values = [];
          res.values.forEach((val) => {
            values.push(val[index]);
          });
          values = [...new Set(values)].filter(Boolean);
          this.$set(item, 'children', values);
          this.$set(item, 'active', res.recommended_values[index]);
          this.$set(item, 'showError', false);
        });
        this.definitions = [...res.definitions];
        console.log('res', this.definitions);
        this.values = [...res.values];
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.message,
        });
        this.$router.push({
          name: 'appService',
          params: {
            id: this.curAppCode,
            moduleId: this.curModuleId,
          },
        });
      } finally {
        this.isLoading = false;
      }
    },


    // 确认启动服务
    async handleConfigChange() {
      this.loading = true;
      const specs = this.definitions.reduce((p, v) => {
        p[v.name] = v.active;
        return p;
      }, {});
      const params = {
        specs,
        service_id: this.curData.uuid,
        module_name: this.curModuleId,
        code: this.curAppCode,
      };
      try {
        await this.$store.dispatch('service/enableServices', params);
        this.$paasMessage({
          limit: 1,
          theme: 'success',
          message: this.$t('服务启用成功'),
        });
        this.init();
        // this.$router.push({
        //   name: 'appServiceInner',
        //   params: {
        //     id: this.curAppCode,
        //     service: this.curData.uuid,
        //     category_id: this.$route.params.category_id,
        //   },
        // });
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.message,
        });
      } finally {
        this.loading = false;
      }
    },

  },
};
</script>

<style lang="scss" scoped>
  .services-container{
    .ps-top-bar{
      padding: 0 20px;
    }
    .image-content{
      background: #fff;
      padding-top: 0;
    }
    .row-img{
      width: 22px;
      height: 22px;
      border-radius: 50%;
    }
    .row-icon{
      cursor: pointer;
    }

    .success-icon{
      font-size: 24px;
      color: #2DCB56;
    }
  }
    .header-title {
        display: flex;
        align-items: center;
        .app-code {
            color: #979BA5;
        }
        .arrows {
            margin: 0 9px;
            transform: rotate(-90deg);
            font-size: 12px;
            font-weight: 600;
            color: #979ba5;
        }
    }
    #switcher-tooltip{
      .item{
        padding: 10px 0;
        cursor: pointer;
        padding: 10px 14px;
        &:hover {
          background: #F5F7FA;
        }
      }
    }
</style>
<style lang="scss">
    .tips-cls{
      .tippy-arrow{
          display: none !important;
        }
      .tippy-tooltip{
        padding: 0 !important;
      }
    }
</style>
