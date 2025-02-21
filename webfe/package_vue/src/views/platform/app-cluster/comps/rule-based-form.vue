<template>
  <div class="rule-assignment-form">
    <!-- 最少两条规则 -->
    <RulesCards
      v-for="(item, i) in cardsList"
      :ref="`card-${i}`"
      :key="i"
      :data="item"
      :order="i"
      :allLength="cardsList.length"
      v-bind="$attrs"
      @add="handleAdd"
      @delete="handleDelete"
      @move="moveArrayItem"
    />
  </div>
</template>

<script>
import RulesCards from './rules-cards.vue';
import { cloneDeep } from 'lodash';

const defaultCardItem = {
  matcher: {
    key: '',
    value: '',
  },
  hasEnv: false,
  clusters: [],
  envClusters: { stag: [], prod: [] },
};

export default {
  name: 'RuleBasedForm',
  components: {
    RulesCards,
  },
  data() {
    return {
      cardsList: [],
    };
  },
  computed: {
    curTenantData() {
      return this.$store.state.tenant.curTenantData;
    },
    allocationPrecedencePolicies() {
      if (!this.curTenantData.policies) {
        return [];
      }
      return this.curTenantData.policies.allocation_precedence_policies || [];
    },
  },
  mounted() {
    if (!this.allocationPrecedencePolicies.length) {
      this.cardsList = [cloneDeep(defaultCardItem), cloneDeep(defaultCardItem)];
      return;
    }
    this.allocationPrecedencePolicies.forEach((item) => {
      const { matcher = {}, policy = {} } = item;
      const defaultKey = 'region_is';
      const [matcherKey = defaultKey] = Object.entries(matcher)[0] || [defaultKey, ''];

      const card = {
        matcher: {
          key: matcherKey,
          value: matcher[defaultKey] ?? '',
        },
        hasEnv: policy.env_specific || false,
        clusters: policy.clusters ?? [],
        envClusters: policy.env_clusters ?? { stag: [], prod: [] },
      };

      this.cardsList.push(card);
    });
  },
  methods: {
    // 添加卡片
    handleAdd(index) {
      this.cardsList.splice(index + 1, 0, cloneDeep(defaultCardItem));
    },
    // 删除单项规则
    handleDelete(index) {
      this.cardsList.splice(index, 1);
    },
    // 移动规则项
    moveArrayItem(index, order) {
      const temp = this.cardsList[index];
      if (order === 'down') {
        // 交换当前索引和下一个索引的元素
        this.$set(this.cardsList, index, this.cardsList[index + 1]);
        this.$set(this.cardsList, index + 1, temp);
      } else {
        this.$set(this.cardsList, index, this.cardsList[index - 1]);
        this.$set(this.cardsList, index - 1, temp);
      }
    },
    // 卡片列表校验
    async validate() {
      let flag = true;
      for (let i = 0; i < this.cardsList.length; i++) {
        try {
          await this.$refs[`card-${i}`][0]?.validate();
        } catch (e) {
          flag = false;
        }
      }
      return {
        flag,
        data: this.cardsList,
      };
    },
    getCurData() {
      return this.cardsList;
    },
  },
};
</script>

<style lang="scss" scoped></style>
