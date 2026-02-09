<template>
  <div>
    <SectionContainer
      :title="$t('预发布环境')"
      class="mb-24"
    >
      <DetailsRow
        :label-width="labelWidth"
        :label="$t('资源配额方案')"
      >
        <div slot="value">
          <template v-if="!isEdit">
            {{ stagPlanName || '--' }}
          </template>
          <bk-select
            v-else
            v-model="stagPlanName"
            style="width: 300px"
            ext-cls="plan-select-cls"
            :disabled="true"
          >
            <bk-option
              :id="stagPlanName"
              :name="stagPlanName"
            ></bk-option>
          </bk-select>
        </div>
      </DetailsRow>
    </SectionContainer>
    <SectionContainer :title="$t('生产环境')">
      <DetailsRow
        :label-width="labelWidth"
        :label="$t('资源配额方案')"
      >
        <div slot="value">
          <template v-if="!isEdit">
            {{ prodPlanName || '--' }}
          </template>
          <bk-select
            v-else
            v-model="prodPlanName"
            style="width: 300px"
            ext-cls="plan-select-cls"
            :disabled="true"
          >
            <bk-option
              :id="prodPlanName"
              :name="prodPlanName"
            ></bk-option>
          </bk-select>
        </div>
      </DetailsRow>
    </SectionContainer>
  </div>
</template>

<script>
import SectionContainer from '@/components/section-container';
import DetailsRow from '@/components/details-row';

export default {
  name: 'DescriptionFile',
  components: {
    SectionContainer,
    DetailsRow,
  },
  props: {
    processData: {
      type: Object,
      default: () => {},
    },
    isEdit: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      labelWidth: 120,
    };
  },
  computed: {
    stagPlanName() {
      // 优先使用环境级别的 plan_name，否则使用模块级别的 plan_name
      return this.processData?.env_overlays?.stag?.plan_name || this.processData?.plan_name || '';
    },
    prodPlanName() {
      return this.processData?.env_overlays?.prod?.plan_name || this.processData?.plan_name || '';
    },
  },
};
</script>
