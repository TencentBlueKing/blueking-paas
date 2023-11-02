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
            v-bk-tooltips="row.labels.join(', ')"
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
        prop="name_en"
      ></bk-table-column>
      <bk-table-column
        :label="$t('触发条件')"
        prop="name_en"
      ></bk-table-column>
      <bk-table-column
        :label="$t('级别')"
        prop="name_en"
      >
        <template slot-scope="{ row }">
          <span class="left-border">{{ row.name_en }}</span>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('通知组')"
        prop="notice_group_ids"
      ></bk-table-column>
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
export default {
  name: 'AlarmStrategy',
  data() {
    return {
      alarmStrategyList: [
        {
          name_en: '致命',
          id: 'ociv0m',
          name: 'w91odi',
          is_enabled: true,
          labels: ['qx2prd', 'pblq1y', '9fs4a3', '7wb4el'],
          notice_group_ids: [
            //通知组列表
            2,
          ],
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

  .left-border {
    border-left: 4px solid #EA3636;
    padding-left: 3px;
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
}
</style>
