<template>
  <div class="itsm-info-item">
    <div>
      <p class="title">{{ title }}</p>
      <div class="info-item" v-for="(item, index) in data" :key="index">
        <div class="label">{{ $t(item.name) }}</div>
        <div class="desc">
          <template v-if="isValidURL(item.value)">
            <a
              :href="item.value"
              target="blank"
            > {{ item.value }} </a>
          </template>
          <template v-else>
            <div v-dompurify-html="item.value" v-if="item.value"></div>
            <div v-else>--</div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
<script>
export default {
  props: {
    data: {
      type: Array,
      default: () => [],
    },
    title: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      itsmData: [],
    };
  },
  methods: {
    // 判断是否为url
    isValidURL(url) {
      const regex = /^(https?|ftp):\/\/[^\s/$.?#].[^\s]*$/i;
      return regex.test(url);
    },
  },
};
</script>

<style lang="scss" scoped>
  .itsm-info-item {
    padding: 16px;
    margin-top: 20px;
    border-radius: 2px;
    box-shadow: 0 2px 4px 0 #1919290d;
    background: #fff;

    .title {
      font-size: 14px;
      font-weight: 700;
      margin-bottom: 8px;
      color: #63656E;
    }

    .info-item {
      display: flex;
      border-top: 1px solid #EAEBF0;
      font-size: 12px;

      &:last-child {
        border-bottom: 1px solid #EAEBF0;
      }

      .label {
        display: flex;
        flex-direction: row-reverse;
        align-items: center;
        padding-right: 16px;
        width: 110px;
        text-align: right;
        background: #FAFBFD;
        color: #979BA5;
      }

      .desc {
        flex: 1;
        line-height: 1.5;
        padding: 10px 20px 10px 16px;
        border-left: 1px solid #F0F1F5;
      }
    }
  }
</style>
