<template>
  <div class="idle-app-dashboard" v-if="idleAppList.length">
    <!-- 闲置看板功能 -->
    <div class="title-wrapper">
      <h3 class="title">{{ $t('闲置应用') }}</h3>
      <span class="update-time">{{ $t('更新于 {t}之前', { t: relativeTime }) }}</span>
    </div>
    <bk-alert
      type="warning"
      :title="$t('近 30 天内没有访问记录，CPU 使用率低于 1% 且近 7 天无使用波动的模块，请尽快下架。')">
    </bk-alert>
    <bk-table
      :data="idleAppList"
      size="small"
      :outer-border="false"
      :span-method="arraySpanMethod"
      v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
      row-class-name="idle-table-row-cls"
      ext-cls="idle-app-dashboard-table">
      <bk-table-column type="expand" width="30">
        <template slot-scope="props">
          <bk-table
            :data="props.row.module_envs"
            :outer-border="false"
            :header-cell-style="{background: 'red', borderRight: 'none'}"
            ext-cls="child-module-table-cls">
            <bk-table-column label="" width="30"></bk-table-column>
            <bk-table-column label="">
              <template slot-scope="{ row: childRow }">
                {{ childRow.module_name }}
              </template>
            </bk-table-column>
            <bk-table-column label="">
              <template slot-scope="{ row: childRow }">
                {{ childRow.env_name === 'prod' ? $t('生产环境') : $t('预发布环境') }}
              </template>
            </bk-table-column>
            <bk-table-column label="">
              <template slot-scope="{ row: childRow }">
                {{ childRow?.memory_quota / 1024 }} G / {{ (childRow?.cpu_quota / 1000).toFixed(2) }} {{ $t('核') }}
              </template>
            </bk-table-column>
            <bk-table-column label="">
              <template slot-scope="{ row: childRow }">
                {{ (childRow?.cpu_usage_avg * 100).toFixed(2) }}%
              </template>
            </bk-table-column>
            <bk-table-column label="">
              <template slot-scope="{ row: childRow }">
                <span v-bk-tooltips="childRow.latest_deployed_at">
                  {{ dayjs(childRow.latest_deployed_at).fromNow() }}
                </span>
              </template>
            </bk-table-column>
            <bk-table-column label="">
              <template slot-scope="{ row: childRow }">
                <bk-button
                  :text="true"
                  title="primary"
                  @click="hanleOfflinesModule(childRow, props.row)">
                  {{ $t('下架') }}
                </bk-button>
              </template>
            </bk-table-column>
          </bk-table>
        </template>
      </bk-table-column>
      <bk-table-column :label="$t('闲置模块')" min-width="150">
        <template slot-scope="{ row }">
          <div class="app-name-wrapper" v-bk-overflow-tips="{ content: `${row.name}（${row.code}）` }">
            <img class="app-logo" :src="row.logo_url" alt="logo" />
            {{ row.name }}<span class="code">（{{ row.code }}）</span>
          </div>
        </template>
      </bk-table-column>
      <bk-table-column :label="$t('环境')" prop="source">
        <template slot-scope="{ row }">
          <tag-box :tags="row.staffList" />
        </template>
      </bk-table-column>
      <bk-table-column :label="$t('资源配额')"></bk-table-column>
      <bk-table-column :label="$t('CPU 使用率')"></bk-table-column>
      <bk-table-column :label="$t('最近部署时间')"></bk-table-column>
      <bk-table-column :label="$t('操作')">
        <template slot-scope="{ row }">
          <bk-button
            :theme="'default'"
            type="submit"
            size="small"
            @click="handleLeaveApp(row)">
            {{ $t('退出应用') }}
          </bk-button>
        </template>
      </bk-table-column>
    </bk-table>

    <!-- 退出应用 -->
    <bk-dialog
      v-model="leaveAppDialog.visiable"
      width="540"
      :title="$t('退出应用')"
      :theme="'primary'"
      :mask-close="false"
      :loading="leaveAppDialog.isLoading"
      @confirm="confirmLeaveApp"
      @cancel="resetScrollPosition"
    >
      <div class="tc">
        {{ $t('退出并放弃此应用的对应权限，是否确定？') }}
      </div>
    </bk-dialog>

    <!-- 下架模块 -->
    <bk-dialog
      v-model="offlineAppDialog.visiable"
      width="450"
      :title="$t('是否下架 {n} 模块', { n: curOperationAppData.module_name })"
      :theme="'primary'"
      :header-position="'left'"
      :mask-close="false"
      :loading="offlineAppDialog.isLoading"
      :ok-text="$t('下架')"
      :cancel-text="$t('取消')"
      @confirm="confirmOfflineApp"
      @cancel="resetScrollPosition"
    >
      <div class="tl">
        {{ $t('将模块从') }}
        <em>{{ curOperationAppData.env_name === 'stag' ? $t('预发布环境') : $t('生产环境') }}</em>
        {{ $t('下架，会停止当前模块下所有进程，增强服务等模块的资源仍然保留。') }}
      </div>
    </bk-dialog>
  </div>
</template>

<script>
import TagBox from './comps/tag-box';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';

export default {
  name: 'IdleAppDashboard',
  components: {
    TagBox,
  },
  data() {
    return {
      idleAppList: [],
      relativeTime: '',
      isTableLoading: false,
      visibleTags: [],
      hiddenCount: 0,
      leaveAppDialog: {
        visiable: false,
        isLoading: false,
        data: {},
      },
      offlineAppDialog: {
        visiable: false,
        isLoading: false,
      },
      curOperationAppData: {},
      scrollPosition: 0,
      dayjs,
    };
  },
  computed: {
    localLanguage() {
      return this.$store.state.localLanguage;
    },
  },
  created() {
    this.getIdleAppList();
    dayjs.extend(relativeTime);
    if (this.localLanguage !== 'en') {
      dayjs.locale('zh-cn');
    }
  },
  methods: {
    // 获取闲置应用看板数据
    async getIdleAppList() {
      this.isTableLoading = true;
      try {
        const res = await this.$store.dispatch('baseInfo/gitIdleAppList');
        // 该应用无模块，则无需展示
        this.idleAppList = res.applications
          .filter(app => app.module_envs.length)
          .map(item => ({
            ...item,
            staffList: [...item.administrators, ...item.developers],
          }));
        this.relativeTime = dayjs(res.collected_at).fromNow(true);
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isTableLoading = false;
      }
    },
    // 合并表格行
    arraySpanMethod({ columnIndex }) {
      if (columnIndex === 2) {
        return [1, 4];
      } if (columnIndex >= 3 && columnIndex <= 5) {
        return [0, 0];
      }
    },
    // 退出应用
    handleLeaveApp(data) {
      this.scrollPosition = window.scrollY || window.pageYOffset || document.documentElement.scrollTop;
      this.leaveAppDialog.visiable = true;
      this.curOperationAppData = data;
    },
    // 确定退出
    async confirmLeaveApp() {
      this.leaveAppDialog.isLoading = true;
      try {
        await this.$store.dispatch('baseInfo/leaveApp', {
          appCode: this.curOperationAppData.code,
        });
        // 退出成功
        this.leaveAppDialog.visiable = false;
        this.resetScrollPosition();
        this.$paasMessage({
          theme: 'success',
          message: this.$t('退出成功'),
        });
        // 重新刷新表格
        this.getIdleAppList();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: `${this.$t('退出应用失败：')} ${e.detail}`,
        });
      } finally {
        this.leaveAppDialog.isLoading = false;
      }
    },
    // 下架模块
    hanleOfflinesModule(data, appData) {
      this.scrollPosition = window.scrollY || window.pageYOffset || document.documentElement.scrollTop;
      this.offlineAppDialog.visiable = true;
      this.curOperationAppData = {
        ...data,
        ...appData,
      };
    },
    // 确定下架
    async confirmOfflineApp() {
      this.offlineAppDialog.isLoading = true;
      try {
        await this.$store.dispatch('baseInfo/offlinesModule', {
          appCode: this.curOperationAppData.code,
          moduleName: this.curOperationAppData.module_name,
          env: this.curOperationAppData.env_name,
        });
        // 下架成功
        this.offlineAppDialog.visiable = false;
        this.resetScrollPosition();
        this.$paasMessage({
          theme: 'success',
          message: this.$t('下架成功'),
        });
        this.getIdleAppList();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('下架失败，请稍候再试'),
        });
      } finally {
        this.offlineAppDialog.isLoading = false;
      }
    },
    // 滚动到记录位置
    resetScrollPosition() {
      this.$nextTick(() => {
        window.scrollTo(0, this.scrollPosition);
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.idle-app-dashboard {
  .title-wrapper {
    display: flex;
    align-items: center;
    margin-bottom: 16px;
    .title {
      font-weight: 700;
      font-size: 16px;
      color: #313238;
      margin-right: 10px;
    }
    .update-time {
      color: #9c9ca0;
      font-size: 12px;
    }
  }
  .idle-app-dashboard-table {
    margin-top: 12px;
  }

  .app-name-wrapper {
    .app-logo {
      width: 16px;
      height: 16px;
      margin-right: 8px;
      vertical-align: middle;
    }
    .code {
      color: #979BA5;
    }
  }

  .tl em {
    font-weight: bold;
  }

  :deep(.idle-app-dashboard-table) .bk-table-body td.bk-table-expanded-cell {
    padding: 0px !important;
  }

  :deep(.idle-app-dashboard-table) {
    .bk-table-body-wrapper .idle-table-row-cls {
      background: #F0F1F5;
    }
    tr.expanded .bk-table-expand-icon .bk-icon {
      color: #63656E;
    }
    .bk-table-expand-icon .bk-icon {
      color: #979BA5;
    }
    .child-module-table-cls .bk-table-header-wrapper {
      display: none;
    }
  }
}
</style>
