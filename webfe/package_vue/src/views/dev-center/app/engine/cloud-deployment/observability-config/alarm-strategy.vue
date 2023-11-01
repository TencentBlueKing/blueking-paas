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
        prop="name_en"
      ></bk-table-column>
      <bk-table-column :label="$t('标签')">
        <template slot-scope="{ row }">
          {{ row.log_type === 'stdout' ? $t('标准输出') : $t('容器内文件') }}
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
      ></bk-table-column>
      <bk-table-column
        :label="$t('通知组')"
        prop="name_en"
      ></bk-table-column>
      <bk-table-column
        :label="$t('是否启用')"
        prop="name_en"
      ></bk-table-column>
    </bk-table>
  </div>
</template>

<script>
export default {
  name: 'AlarmStrategy',
  data() {
    return {
      alarmStrategyList: [],
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
</style>
