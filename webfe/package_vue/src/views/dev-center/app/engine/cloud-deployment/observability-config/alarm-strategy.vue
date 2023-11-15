<template>
  <div class="alarm-strategy mt25">
    <div class="top-title mb20">
      <h4>{{ $t('告警策略') }}</h4>
      <p class="tips">
        {{ $t('如需新增或编辑告警策略请直接到蓝鲸监控平台操作。') }}
        <span class="customize">
          <i class="paasng-icon paasng-jump-link"></i>
          {{ $t('配置告警策略') }}
        </span>
      </p>
    </div>
    <!-- 策略列表 -->
    <bk-table
      :data="alarmStrategyList"
      size="small"
      ext-cls="collection-rules-cls"
      :outer-border="false"
      :header-border="false"
      :pagination="pagination"
    >
      <bk-table-column
        :label="$t('策略名')"
        prop="name"
        :show-overflow-tooltip="true"
      ></bk-table-column>
      <bk-table-column :label="$t('标签')">
        <template slot-scope="{ row }">
          <div
            v-if="row.labels.length"
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
      >
        <template slot-scope="{ row }">
          {{ row.triggerCondition }}
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('级别')"
      >
        <template slot-scope="{ row }">
          <span :class="['level-border', `level${row.levelText.id}`]">
            {{ row.levelText && $t(row.levelText.text) }}
          </span>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('通知组')"
      >
        <template slot-scope="{ row }">
          <div
            v-if="row.noticeGroupNames.length"
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
          <span :class="['tag', row.is_enabled ? 'enable' : 'deactivate' ]">{{ row.is_enabled ? '启用' : '停用' }}</span>
        </template>
      </bk-table-column>
    </bk-table>
  </div>
</template>

<script>
import { THRESHOLD_MAP, LEVEL_MAP } from '@/common/constants.js';

export default {
  name: 'AlarmStrategy',
  data() {
    return {
      alarmStrategyList: [
        {
          name_en: '',
          id: '',
          name: '',
          is_enabled: true,
          labels: [],
          notice_group_ids: [],
          detects: [
            {
              trigger_config: {
                // 触发策略，count/check_window = 触发时机
                count: 1,
                check_window: 6,
              },
            },
          ],
        },
      ],
      // 是否需要分页
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
      },
    };
  },
  computed: {
    appCode() {
      return this.$route.params.id;
    },
  },
  created() {
    this.getAlarmStrategies();
  },
  methods: {
    // 获取告警策略
    async getAlarmStrategies() {
      try {
        const { strategy_config_list: strategyList, user_group_list } = await this.$store.dispatch('alarm/getAlarmStrategies', {
          appCode: this.appCode,
        });

        strategyList.forEach((v) => {
          // 用户组处理
          v.noticeGroupNames = v.notice_group_ids.map((id) => {
            // eslint-disable-next-line camelcase
            const foundItem = user_group_list.find(userItem => +userItem.user_group_id === id);
            return foundItem ? foundItem.user_group_name : null;
          });

          // 触发条件处理
          if (v.detects.length) {
            const config = v.detects[0].trigger_config;
            v.triggerCondition = `${config.count}/${config.check_window}`;
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
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
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
    font-weight: 400;
  }
  .customize {
    color: #3a84ff;
    cursor: pointer;
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
      color: #18B456;
      background: #DCFFE2;
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
</style>
