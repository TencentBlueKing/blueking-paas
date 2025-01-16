<template>
  <div class="rule-assignment-form">
    <RulesCards
      v-for="(item, i) in data"
      :key="item"
      :conditional="getConditionalType(data.length, i)"
    />
  </div>
</template>

<script>
import RulesCards from './rules-cards.vue';
export default {
  name: 'RuleBasedForm',
  components: {
    RulesCards,
  },
  data() {
    return {
      data: [1, 2],
      cardsList: [
        {
          hasEnv: false,
        },
      ],
    };
  },
  methods: {
    // 获取当前规则语句分支
    getConditionalType(arrayLength, currentIndex) {
      if (currentIndex === 0) {
        return 'if';
      } else if (currentIndex === arrayLength - 1) {
        return 'else';
      } else {
        return 'else if';
      }
    },
  },
};
</script>

<style lang="scss" scoped></style>
