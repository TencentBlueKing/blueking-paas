<template>
  <div class="idle-app-dashboard" v-if="idleAppList.length">
    <!-- 闲置看板功能 -->
    <!-- <div class="title-wrapper">
      <h3 class="title">{{ $t('闲置应用') }}</h3>
      <span class="update-time">{{ $t('更新于 {t}之前', { t: relativeTime }) }}</span>
    </div> -->
    <bk-alert
      type="warning"
      :title="$t('近 30 天内没有访问记录，CPU 使用率低于 1% 且近 7 天无使用波动的模块，请尽快下架。')">
    </bk-alert>
    <bk-table
      :data="idleAppList"
      size="small"
      :outer-border="false"
      :span-method="arraySpanMethod"
      :row-key="rowKey"
      :expand-row-keys="expandRowKeys"
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
            <bk-table-column label="" width="240">
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
                <bk-popover
                  :ref="`removed${childRow.env_name}-${childRow.module_name}`"
                  placement="top"
                  theme="light-border"
                  trigger="click"
                  width="260"
                  :on-hide="handleHide"
                  ext-cls="idle-popover-cls">
                  <bk-button
                    :text="true"
                    :title="$t('下架')"
                    @click="handleShowPopover(childRow, props.row)">
                    {{ $t('下架') }}
                  </bk-button>
                  <div slot="content">
                    <div class="popover-title">{{ $t('是否下架 {n} 模块', { n: curOperationAppData.module_name }) }}</div>
                    <div class="popover-content tl">
                      {{ $t('将模块从') }}
                      <em>{{ curOperationAppData.env_name === 'stag' ? $t('预发布环境') : $t('生产环境') }}</em>
                      {{ $t('下架，会停止当前模块下所有进程，增强服务等模块的资源仍然保留。') }}
                    </div>
                    <div class="popover-operate">
                      <bk-button
                        :theme="'primary'"
                        size="small"
                        class="mr4"
                        :loading="isPopoverLoading"
                        @click="handleConfirm('offlineApp', `removed${childRow.env_name}-${childRow.module_name}`)">
                        {{ $t('确定') }}
                      </bk-button>
                      <bk-button
                        :theme="'default'"
                        size="small"
                        @click="handleCancel(`removed${childRow.env_name}-${childRow.module_name}`)">
                        {{ $t('取消') }}
                      </bk-button>
                    </div>
                  </div>
                </bk-popover>
                <!-- 忽略 -->
                <bk-popover
                  :ref="`ignore${childRow.env_name}-${childRow.module_name}`"
                  placement="top"
                  theme="light-border"
                  trigger="click"
                  width="260"
                  :on-hide="handleHide"
                  ext-cls="idle-popover-cls">
                  <bk-button
                    :text="true"
                    class="ml10"
                    :title="$t('忽略')"
                    @click="handleShowPopover(childRow, props.row)">
                    {{ $t('忽略') }}
                  </bk-button>
                  <div slot="content">
                    <div class="popover-title">
                      {{ $t('是否忽略 {n} 模块闲置提醒？', { n: curOperationAppData.module_name }) }}
                    </div>
                    <div class="popover-content tl">
                      {{ $t('忽略后，该模块的') }}
                      <em>{{ curOperationAppData.env_name === 'stag' ? $t('预发布环境') : $t('生产环境') }}</em>
                      {{ $t('将在 6 个月内不出现在闲置应用列表中，若 6 个月后继续闲置，将重新提醒。') }}
                    </div>
                    <div class="popover-operate">
                      <bk-button
                        :theme="'primary'"
                        size="small"
                        class="mr4"
                        :loading="isPopoverLoading"
                        @click="handleConfirm('ignoreModule', `ignore${childRow.env_name}-${childRow.module_name}`)">
                        {{ $t('忽略') }}
                      </bk-button>
                      <bk-button
                        :theme="'default'"
                        size="small"
                        @click="handleCancel(`ignore${childRow.env_name}-${childRow.module_name}`)">
                        {{ $t('取消') }}
                      </bk-button>
                    </div>
                  </div>
                </bk-popover>
              </template>
            </bk-table-column>
          </bk-table>
        </template>
      </bk-table-column>
      <bk-table-column :label="$t('闲置模块')" width="240">
        <template slot-scope="{ row }">
          <div
            class="app-name-wrapper"
            v-bk-overflow-tips="{ content: `${row.name}（${row.code}）` }"
            @click="toAppDetail(row)"
          >
            <img class="app-logo" :src="row.logo_url" alt="logo" />
            <span class="info">{{ row.name }}<span class="code">（{{ row.code }}）</span></span>
          </div>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('环境')"
        prop="source"
        class-name="env-column-cls">
        <template slot-scope="{ row }">
          <tag-box :tags="row.staffList" />
          <bk-popover
            :ref="`quit${row.code}`"
            placement="top"
            theme="light-border"
            trigger="click"
            width="260"
            :on-hide="handleHide"
            ext-cls="idle-popover-cls">
            <bk-button
              :theme="'default'"
              type="submit"
              size="small"
              @click="handleLeaveApp(row)">
              {{ $t('退出应用') }}
            </bk-button>
            <div slot="content">
              <div class="popover-title">{{ $t('退出应用') }}</div>
              <div class="popover-content">{{ $t('退出并放弃此应用的对应权限，是否确定？') }}</div>
              <div class="popover-operate">
                <bk-button
                  :theme="'primary'"
                  size="small"
                  class="mr4"
                  :loading="isPopoverLoading"
                  @click="confirmLeaveApp(`quit${row.code}`)">
                  {{ $t('确定') }}
                </bk-button>
                <bk-button
                  :theme="'default'"
                  size="small"
                  @click="handleCancel(`quit${row.code}`)">
                  {{ $t('取消') }}
                </bk-button>
              </div>
            </div>
          </bk-popover>
        </template>
      </bk-table-column>
      <bk-table-column :label="$t('资源配额')"></bk-table-column>
      <bk-table-column :label="$t('CPU 使用率')"></bk-table-column>
      <bk-table-column :label="$t('最近部署时间')"></bk-table-column>
      <bk-table-column :label="$t('操作')"></bk-table-column>
    </bk-table>
  </div>
</template>

<script>
import TagBox from '../comps/tag-box';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';
import { bus } from '@/common/bus';

export default {
  name: 'IdleAppDashboard',
  components: {
    TagBox,
  },
  data() {
    return {
      idleAppList: [],
      expandRowKeys: [],
      relativeTime: '',
      isTableLoading: true,
      visibleTags: [],
      hiddenCount: 0,
      curOperationAppData: {},
      dayjs,
      isPopoverLoading: false,
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
        const res = await this.$store.dispatch('baseInfo/getIdleAppList');
        // 该应用无模块，则无需展示
        this.idleAppList = res.applications
          .filter(app => app.module_envs.length)
          .map(item => ({
            ...item,
            staffList: [...item.administrators, ...item.developers],
          }));
        if (this.idleAppList.length) {
          this.expandRowKeys.push(this.idleAppList[0].code);
        }
        this.relativeTime = dayjs(res.collected_at).fromNow(true);
        this.$emit('async-list-length', {
          name: 'idle',
          length: this.idleAppList.length,
        });
        // 闲置应用数
        this.$store.commit('baseInfo/updateAppChartData', {
          idleAppCount: this.idleAppList.length,
          updateTime: this.relativeTime,
        });
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isTableLoading = false;
        bus.$emit('on-close-loading');
      }
    },
    // 行key
    rowKey(row) {
      return row.code;
    },
    // 合并表格行
    arraySpanMethod({ columnIndex }) {
      if (columnIndex === 2) {
        return [1, 5];
      } if (columnIndex >= 3 && columnIndex <= 5) {
        return [0, 0];
      }
    },
    // 退出应用
    handleLeaveApp(data) {
      this.curOperationAppData = data;
    },
    // 确定退出
    async confirmLeaveApp(refName) {
      this.isPopoverLoading = true;
      try {
        await this.$store.dispatch('member/quitApplication', {
          appCode: this.curOperationAppData.code,
        });
        this.handleCancel(refName);
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
        this.isPopoverLoading = false;
      }
    },
    // 下架/忽略模块
    handleShowPopover(data, appData) {
      this.curOperationAppData = {
        ...data,
        ...appData,
      };
    },
    // 确定下架/忽略
    async handleConfirm(name, refName) {
      const dispatchName = `deploy/${name}`;
      this.isPopoverLoading = true;
      try {
        await this.$store.dispatch(dispatchName, {
          appCode: this.curOperationAppData.code,
          moduleId: this.curOperationAppData.module_name,
          env: this.curOperationAppData.env_name,
        });
        this.handleCancel(refName);
        this.$paasMessage({
          theme: 'success',
          message: name === 'offlineApp' ? this.$t('下架成功') : this.$t('忽略成功'),
        });
        this.getIdleAppList();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || (name === 'offlineApp' ? this.$t('下架失败，请稍候再试') : this.$t('忽略失败，请稍候再试')),
        });
      } finally {
        this.isPopoverLoading = false;
      }
    },
    // 应用详情
    toAppDetail(row) {
      if (row.is_plugin_app) {
        this.$router.push({
          name: 'pluginSummary',
          params: { pluginTypeId: 'bk-saas', id: row.code },
        });
        return;
      }
      this.$router.push({
        name: row.type === 'cloud_native' ? 'cloudAppSummary' : 'appSummary',
        params: { id: row.code },
      });
    },
    handleHide() {
      this.isPopoverLoading = false;
    },
    // 取消
    handleCancel(refName) {
      this.$refs[refName].hideHandler();
    },
  },
};
</script>

<style lang="scss" scoped>
.idle-app-dashboard {
  .title-wrapper {
    display: flex;
    align-items: center;
    width: 100%;
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
    cursor: pointer;
    .app-logo {
      width: 16px;
      height: 16px;
      margin-right: 8px;
      vertical-align: middle;
    }
    .code {
      color: #979BA5;
    }
    .info:hover {
      color: #3A84FF;
    }
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
    .env-column-cls .cell {
      display: flex;
      align-items: center;
    }
  }
}

.mr4 {
  margin-right: 4px;
}

.idle-popover-cls {
  .popover-title {
    font-size: 14px;
    color: #313238;
    margin-bottom: 10px;
  }
  .popover-content {
    margin-bottom: 10px;
  }
  .popover-operate {
    text-align: right;
  }
  .tl em {
    font-weight: bold;
  }
}
</style>
