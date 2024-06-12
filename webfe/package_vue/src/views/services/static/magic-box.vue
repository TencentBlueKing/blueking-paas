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
        name: 'MagicBox',
        apititle: 'MagicBox',
        hasLink: true,
        link: this.GLOBAL.LINK.MAGICBOX_INDEX,
        image: '/static/images/service-pic8.png',
        apiexplain: this.$t('蓝鲸MagicBox提供丰富的PC端、移动端前端UI组件，更有样例套餐助您快速搭建前端页面。同时蓝鲸MagicBox提供可视化开发服务，支持在线拖拽页面，所见即所得。'),
        apiList: [
          {
            title: this.$t('运维开发平台'),
            explain: this.$t('支持在线拖拽，使用MagicBox提供的组件，自由布局页面。'),
            url: this.GLOBAL.LINK.LESSCODE_INDEX,
          },
          {
            title: this.$t('前端jQuery组件库'),
            explain: this.$t('提供表单、表格、富文本、按钮等丰富的UI组件，包括PC版、移动版。'),
            url: this.GLOBAL.LINK.MAGICBOX_JQUERY,
          },
          {
            title: this.$t('前端Vue组件库'),
            explain: this.$t('基于 Vue2.0、Vue3.0，提供按钮、下拉选框、日期选择器、对话框等常用组件。'),
            url: this.GLOBAL.LINK.MAGICBOX_VUE,
          },
          {
            title: this.$t('前端套餐样例库'),
            explain: this.$t('提供成套的样例页面，即拿即用。'),
            url: this.GLOBAL.LINK.MAGICBOX_TPL,
          },
          {
            title: this.$t('蓝鲸前端开发脚手架（BKUI_CLI）'),
            explain: this.$t('基于 Vue.js 研发的一键构建蓝鲸体系前端工程的脚手架工具，包括了基础工程化能力、基础 mock 服务、蓝鲸前端Vue组件库等。'),
            url: this.GLOBAL.LINK.MAGICBOX_BKUI_CLI,
            isDoc: true,
          },
        ],
      },
    };
  },
};
</script>

<style lang="css" scoped>
    .paasng-angle-double-right {
        padding-left: 3px;
        font-size: 12px;
        font-weight: bold;
    }
</style>
