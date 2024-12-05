<template lang="html">
  <service-general :data="apiData" />
</template>

<script>
import serviceGeneral from '@/components/serviceGeneral';
export default {
  components: {
    serviceGeneral,
  },
  data() {
    return {
      apiData: {
        name: this.$t('流程引擎'),
        apititle: this.$t('流程引擎'),
        image: '/static/images/ModBpm.png',
        apiexplain: this.$t('标准运维V3使用的分布式的流程定义、管理、调度引擎。'),
        hasLink: true,
        link: this.GLOBAL.LINK.BAMBOO_CODE,
        apiList: [
          {
            title: this.$t('来自标准运维 v3'),
            explain: this.$t(
              'Bamboo 可以解析、管理、执行由用户创建的流程任务，提供了如暂停、继续、撤销、跳过和重试等灵活的任务控制能力，并且支持子流程，流程串行、并行、分支、循环、打回控制等进阶特性。',
            ),
          },
          {
            title: this.$t('简易的流程构造方式'),
            explain: this.$t('可以使用 Bamboo 提供的 builder 轻松地构造复杂的流程。'),
          },
          {
            title: this.$t('完整的流程控制特性'),
            explain: this.$t(
              'Bamboo 支持基本的流程启动、暂停、继续、重试和撤销，以及流程串行、并行、分支、循环、打回控制等进阶特性。',
            ),
          },
          {
            title: this.$t('足够的并发处理效率'),
            explain: this.$t(
              '基于 Celery，通过将不同性质的任务划分到不同的队列， Bamboo 拥有足够的执行效率，并且可通过水平扩展来进一步提升并发处理能力。',
            ),
          },
          {
            title: this.$t('帮助文档 ：'),
            explain: this.$t('快速开始'),
            explainIsLink: true,
            url: this.GLOBAL.LINK.BAMBOO_CODE,
          },
        ],
      },
    };
  },
};
</script>
