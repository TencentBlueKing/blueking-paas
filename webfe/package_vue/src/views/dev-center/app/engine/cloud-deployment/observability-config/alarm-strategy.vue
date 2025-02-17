<template>
  <div class="alarm-strategy mt25">
    <div class="top-title mb20">
      <h4>{{ $t('告警策略') }}</h4>
      <p class="tips" v-if="platformFeature.MONITORING">
        {{ $t('告警策略对应用下所有模块都生效，如需新增或编辑告警策略请直接到蓝鲸监控平台操作。') }}
        <!-- 未部署不展示 -->
        <a v-if="strategyLink" :href="strategyLink" target="_blank">
          <i class="paasng-icon paasng-jump-link"></i>
          {{ $t('配置告警策略') }}
        </a>
      </p>
    </div>

    <div
      v-bkloading="{ isLoading: isLoading, zIndex: 10 }"
      v-if="platformFeature.MONITORING"
    >
      <!-- 策略列表 -->
      <bk-table
        v-if="alarmStrategyList?.length"
        :data="alarmStrategyList"
        size="small"
        ext-cls="alarm-strategy-cls"
        :outer-border="false"
        :header-border="false"
        :pagination="pagination"
      >
        <bk-table-column
          :label="$t('策略名')"
          :show-overflow-tooltip="true"
        >
          <template slot-scope="{ row }">
            <a :href="row.detail_link" target="_blank">
              {{ row.name }}
            </a>
          </template>
        </bk-table-column>
        <bk-table-column :label="$t('标签')">
          <template slot-scope="{ row }">
            <div
              v-if="row.labels?.length"
              v-bk-overflow-tips="{ content: row.labels.join(', ') }"
            >
              <span
                v-for="item in row.labels"
                :key="item"
                class="td-tag"
              >
                {{ item }}
              </span>
            </div>
            <span v-else>--</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('阈值')"
        >
          <template slot-scope="{ row }">
            {{ row.maxThresholdConfig && row.maxThresholdConfig.text }}
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('触发条件')"
          :show-overflow-tooltip="false"
        >
          <template slot-scope="{ row }">
            <span v-bk-tooltips="$t(`在 ${row.algorithm} 个周期内累计满足 ${row.cycle} 次检测算法，触发告警通知`)">
              {{ `${row.cycle || '--'}/${row.algorithm || '--'}` }}
            </span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('级别')"
        >
          <template slot-scope="{ row }">
            <span :class="['level-border', `level${row.levelText?.id}`]">
              {{ row.levelText && $t(row.levelText.text) }}
            </span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('通知组')"
        >
          <template slot-scope="{ row }">
            <div
              v-if="row.noticeGroupNames?.length"
              v-bk-overflow-tips="{ content: row.noticeGroupNames.join(', ') }"
            >
              <span
                v-for="item in row.noticeGroupNames"
                :key="item"
                class="td-tag"
              >
                <template v-if="item !== null">{{ item }}</template>
              </span>
            </div>
            <span v-else>--</span>
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('是否启用')"
          prop="is_enabled"
        >
          <template slot-scope="{ row }">
            <span :class="['tag', row.is_enabled ? 'enable' : 'deactivate']">
              {{ row.is_enabled ? $t('启用') : $t('停用') }}
            </span>
          </template>
        </bk-table-column>
      </bk-table>
      <div
        v-else
        class="empty"
      >
        <div class="empty-content">
          <div class="title">{{ $t('暂未启用告警策略') }}</div>
          <div class="sub-title">{{ $t('在应用部署成功后，才会配置相应环境的告警策略') }}</div>
          <bk-button :text="true" title="primary" size="small" @click="handleToDeploy">
            {{ $t('去部署') }}
          </bk-button>
        </div>
      </div>
    </div>
    <FunctionalDependency
      v-else
      mode="partial"
      :title="$t('暂无监控告警功能')"
      :functional-desc="$t('开发者中心与蓝鲸监控平台无缝集成，应用部署后便可自动开启资源使用率、进程异常等告警配置。')"
      :guide-title="$t('如需要该功能，需要部署：')"
      :guide-desc-list="[$t('1. 蓝鲸监控：监控日志套餐')]"
      @gotoMore="gotoMore"
    />
  </div>
</template>

<script>
import FunctionalDependency from '@blueking/functional-dependency/vue2/index.umd.min.js';
import { THRESHOLD_MAP, LEVEL_MAP } from '@/common/constants.js';

export default {
  name: 'AlarmStrategy',
  components: { FunctionalDependency },
  data() {
    return {
      alarmStrategyList: [],
      // 是否需要分页
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
      },
      strategyLink: '',
      isLoading: false,
    };
  },
  computed: {
    appCode() {
      return this.$route.params.id;
    },
    platformFeature() {
      return this.$store.state.platformFeature;
    },
  },
  created() {
    if (this.platformFeature.MONITORING) {
      this.getAlarmStrategies();
    }
  },
  methods: {
    // 获取告警策略
    async getAlarmStrategies() {
      this.isLoading = true;
      try {
        const res = await this.$store.dispatch('alarm/getAlarmStrategies', {
          appCode: this.appCode,
        });

        // 未部署处理
        const strategyList = res.strategy_config_list || [];
        const userGroupList = res.user_group_list || [];
        const strategyConfigLink = res.strategy_config_link || '';

        strategyList.length && strategyList.forEach((v) => {
          // 用户组处理
          v.noticeGroupNames = v.notice_group_ids.map((id) => {
            // eslint-disable-next-line camelcase
            const foundItem = userGroupList.find(userItem => +userItem.user_group_id === id);
            return foundItem ? foundItem.user_group_name : null;
          });

          // 触发条件处理
          if (v.detects.length) {
            const config = v.detects[0].trigger_config;
            v.cycle = config.count;
            v.algorithm = config.check_window;
          }
          // 阈值&级别处理
          if (v.items.length) {
            // 最大阈值
            let maxThreshold = -1;
            // 最大阈值config
            let maxThresholdConfig = {};
            // 级别
            let level = {};

            v.items.forEach((item) => {
              // 算法 1: N
              const { algorithms } = item;
              algorithms.forEach((algorithmItem) => {
                // 级别转换
                level = { id: algorithmItem.level, text: LEVEL_MAP[algorithmItem.level - 1] };

                // type 为 Threshold 才展示阈值
                if (algorithmItem.type === 'Threshold') {
                  // 算法配置 [[{配置}]]
                  const { config } = algorithmItem;
                  config.forEach((innerArray) => {
                    innerArray.forEach((obj) => {
                      if (obj.threshold && obj.threshold > maxThreshold) {
                        maxThreshold = innerArray[0].threshold;
                        // eslint-disable-next-line prefer-destructuring
                        maxThresholdConfig = innerArray[0];
                      }
                    });
                  });
                }
              });
            });

            maxThresholdConfig.text = maxThreshold === -1 ? '--' : `${THRESHOLD_MAP[maxThresholdConfig.method]}${maxThresholdConfig.threshold}`;
            v.maxThresholdConfig = maxThresholdConfig;
            v.levelText = level;
          }
        });
        this.alarmStrategyList = strategyList;
        // eslint-disable-next-line camelcase
        this.strategyLink = strategyConfigLink;
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally  {
        this.isLoading = false;
      }
    },
    handleToDeploy() {
      this.$router.push({
        name: 'cloudAppDeployManageStag',
        params: {
          id: this.appCode,
        },
      });
    },
    // 了解更多
    gotoMore() {
      window.open(this.GLOBAL.DOC.MONITORING_FEATURE_DOC, '_blank');
    },
  },
};
</script>

<style lang="scss" scoped>
.top-title {
  font-size: 12px;
  display: flex;
  align-content: center;
  color: #979ba5;

  h4 {
    font-size: 14px;
    color: #313238;
    padding: 0;
    margin-right: 16px;
    font-weight: 700;
  }
}
.alarm-strategy {
  .td-tag {
    display: inline-block;
    height: 22px;
    line-height: 22px;
    padding: 0 8px;
    background: #f0f1f5;
    border-radius: 2px;
    margin-right: 4px;
    color: #63656e;

    &:last-child {
      margin-right: 0;
    }
  }

  .tag {
    display: inline-block;
    height: 22px;
    line-height: 22px;
    padding: 0 4px;
    border-radius: 2px;

    &.deactivate {
      color: #979BA5;
      background: #F0F1F5;
    }
    &.enable {
      color: #14A568;
      background: #E4FAF0;
    }
  }

  .level-border {
    padding-left: 4px;

    &.level1 {
      border-left: 4px solid #EA3636;
    }
    &.level2 {
      border-left: 4px solid #FF9C01;
    }
    &.level3 {
      border-left: 4px solid #3A84FF;
    }
  }
}

.alarm-strategy-cls {
  /deep/ .bk-table-row-last td {
    border-bottom: none !important;
  }
}

.empty {
  margin-top: 26px;
  display: flex;
  justify-content: center;
  .empty-content {
    text-align: center;
    .title {
      font-size: 14px;
      color: #63656E;
      line-height: 24px;
    }

    .sub-title {
      margin: 8px 0;
      font-size: 12px;
      color: #979BA5;
      line-height: 20px;
    }
  }
}
</style>
