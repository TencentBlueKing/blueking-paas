<template lang="html">
  <div class="right-main bk-service-overview">
    <div class="overview-tit">
      <h2>
        <span class="expert">
          <router-link :to="{ name: 'serviceVas' }">{{ $t('增强服务') }}</router-link>
        </span>
        {{ serviceObject.display_name }}
      </h2>
    </div>

    <paas-content-loader
      class="services-overview-container card-style"
      :is-loading="loading"
      placeholder="service-inner-loading"
    >
      <div :class="{ fadeIn: !loading }">
        <div
          v-if="!loading"
          class="middle bnone"
        >
          <div class="service-ex">
            <img
              :src="serviceObject.logo"
              class="service-ex-img"
              alt=""
            />
            <h2>{{ serviceObject.display_name }}</h2>
            <p>
              <span
                v-for="(item, index) in serviceObject.available_languages"
                :key="index"
                :class="['box green', { purple1: index === 1 }, { purple2: index === 2 }]"
              >
                {{ item }}
              </span>
            </p>
          </div>
          <div class="service-p">
            <h3>{{ $t('服务简介：') }}</h3>
            <p>{{ serviceObject.description }}</p>
          </div>
          <div class="service-p">
            <h3>{{ $t('服务说明：') }}</h3>
            <p>
              <span v-if="serviceObject.long_description">{{ serviceObject.long_description }}，</span>
              <a
                :href="GLOBAL.DOC.SERVICE_INDEX"
                target="_blank"
              >
                {{ $t('查看帮助文档') }}
              </a>
            </p>
          </div>
        </div>

        <div class="enable">
          <h2>
            {{ $t('您有') }}
            <span class="ps-btn-xs">{{ pageConf.count }}</span>
            {{ $t('款应用已启用该服务') }}
          </h2>
          <bk-table
            v-bkloading="{ isLoading: isTableLoading }"
            :data="attList"
            :size="'small'"
            :empty-text="$t('暂无应用启用该服务')"
            :pagination="pageConf"
            :show-pagination-info="true"
            :header-border="false"
            @page-change="handlePageChange"
            @page-limit-change="handlePageSizeChange"
          >
            <div slot="empty">
              <table-empty empty />
            </div>
            <bk-table-column
              :label="$t('应用信息')"
              min-width="200"
              :render-header="$renderHeader"
            >
              <template slot-scope="props">
                <div
                  class="ps-table-app flex-row"
                  @click="toServiceInner(props.row)"
                >
                  <img
                    :src="
                      props.row.application
                        ? props.row.application.logo_url
                          ? props.row.application.logo_url
                          : defaultImg
                        : defaultImg
                    "
                    class="fleft applogo"
                  />
                  <span class="app-name-text">
                    <em>{{ props.row.application.name }}</em>
                  </span>
                </div>
              </template>
            </bk-table-column>
            <bk-table-column
              :label="$t('模块')"
              prop="module_name"
            />
            <bk-table-column
              :label="$t('启用时间')"
              prop="created"
              :render-header="renderHeader"
            />
            <bk-table-column
              :label="$t('应用版本')"
              :render-header="$renderHeader"
            >
              <template slot-scope="props">
                <span>{{ lauguageMap[props.row.region] || '--' }}</span>
              </template>
            </bk-table-column>
            <bk-table-column :label="$t('操作')">
              <template slot-scope="props">
                <div class="table-operate-buttons">
                  <bk-button
                    theme="primary"
                    size="small"
                    text
                    @click="userDetail(props.row)"
                  >
                    {{ $t('使用详情') }}
                  </bk-button>
                </div>
              </template>
            </bk-table-column>
          </bk-table>
        </div>
      </div>
    </paas-content-loader>
  </div>
</template>

<script>
export default {
  data() {
    return {
      serviceObject: {
        logo: '',
        display_name: '',
        available_languages: [],
        description: '',
        long_description: '',
      },
      attList: [],
      orderBy: 'created',
      is_up: true,
      loading: true,
      defaultImg: '/static/images/default_logo.png',
      isTableLoading: false,
      pageConf: {
        current: 1,
        limit: 10,
        limitList: [5, 10, 20, 50],
        count: 0,
      },
      lauguageMap: {
        ieod: this.$t('内部版'),
        tencent: this.$t('外部版'),
        clouds: this.$t('混合云版'),
      },
    };
  },
  computed: {
    curCategoryId() {
      return this.$route.params.category_id;
    },
  },
  watch: {
    'pageConf.current'(value) {
      this.getDataByPage(value);
    },
  },
  created() {
    this.getDataByPage(1);
  },
  methods: {
    renderHeader(h) {
      return h('div', [
        h('span', {
          domProps: {
            innerHTML: this.$t('启用时间'),
          },
        }),
        h('img', {
          style: {
            position: 'relative',
            top: '1px',
            left: '1px',
            cursor: 'pointer',
            transform: this.is_up ? 'rotate(0)' : 'rotate(180deg)',
          },
          attrs: {
            src: '/static/images/sort-icon.png',
          },
          on: {
            click: this.sortTab,
          },
        }),
      ]);
    },

    toServiceInner(item) {
      this.$router.push({
        name: item.application.type === 'cloud_native' ? 'appServices' : 'appServiceInner',
        params: {
          service: item.service,
          id: item.application.code,
          category_id: this.curCategoryId,
          moduleId: item.module_name,
        },
      });
    },

    sortTab() {
      this.orderBy = this.orderBy === 'created' ? '' : 'created';
      this.getDataByPage(1);
      this.is_up = !this.is_up;
    },

    userDetail(item) {
      this.$router.push({
        name: item.application.type === 'cloud_native' ? 'appServices' : 'appServiceInner',
        params: {
          service: item.service,
          id: item.application.code,
          moduleId: item.module_name,
        },
      });
    },

    handlePageChange(page) {
      this.pageConf.current = page;
    },

    handlePageSizeChange(newVal) {
      this.pageConf.limit = newVal;
      this.getDataByPage(1);
    },

    async getDataByPage(page = 1) {
      try {
        this.isTableLoading = true;
        const response = await this.$store.dispatch('tool/getEnabledServiceAppList', {
          name: this.$route.params.name,
          params: {
            offset: (page - 1) * this.pageConf.limit,
            limit: this.pageConf.limit,
            order_by: this.orderBy,
          },
        });
        const { results, count } = response;
        this.serviceObject = {
          ...results,
          available_languages: (results.available_languages || '').split(','),
        };
        this.pageConf.count = count || 0;
        this.attList = results.instances;
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.loading = false;
        this.isTableLoading = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.sort-time,
.shaixuan,
.shaixuan input {
  cursor: pointer;
}

.sort-time {
  margin-left: 3px;
  vertical-align: -1px;
  transform: rotate(180deg);
}

.upsort {
  transform: rotate(0);
}

.shaixuan:hover {
  color: #3a84ff;
}

.itsname {
  display: inline-block;
  position: relative;
  width: 150px;
  line-height: 16px;
}

.applogo {
  margin-right: 13px;
  width: 32px;
  height: 32px;
  border-radius: 4px;
}

.app-name-text {
  display: inline-block;
  width: 210px;
  height: 32px;
  line-height: 32px;
  vertical-align: top;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #3a84ff;
  &:hover {
    color: #699df4;
  }
}

.app-name-text em {
  display: inline-block;
  line-height: 16px;
  vertical-align: middle;
}

.ps-table-app {
  cursor: pointer;
}

.ps-table th.pl30,
.ps-table td.pl30 {
  padding-left: 30px;
}

.ps-table tr:hover {
  .ps-table-app {
    color: #3a84ff;
  }
}

.enable h2 {
  padding: 0 0 7px 0;
  font-size: 14px;
  line-height: 40px;
  color: #55545a;
  font-weight: bold;
  span {
    color: #2dcb56;
  }
}

.page-wrapper {
  text-align: center;
  margin-top: 20px;
}

.services-overview-container {
  background: #fff;
  padding: 10px 24px 24px;
  margin: 20px 24px;
}

.overview-tit {
  background: #fff;
  box-shadow: 0 2px 4px 0 #1919290d;
  h2 {
    border: none;
  }
}
</style>
