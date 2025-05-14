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
        name: this.$t('工蜂 Copilot'),
        hasLink: true,
        link: window.BK_TCGIT_COPILOT_URL,
        apititle: this.$t('工蜂 Copilot'),
        image: '/static/images/tc_git.png',
        apiexplain: this.$t('工蜂 Copilot 是由工蜂智能化团队推出的一款 AI 代码助手工具。采用腾讯混元代码领域大模型，同时结合开源模型、以及工蜂领域数据进行业务精调。'),
        apiList: [
          {
            title: this.$t('代码补全与生成目前支持语言'),
            explain: this.$t('Python, JavaScript/TypeScript, Java, C/C++, Go, C#, Lua, Kotlin, TSX/JSX, Vue, Proto, PHP 等 100+ 语言/框架'),
          },
          {
            title: this.$t('目前支持 IDE'),
            explain: this.$t('Visual Studio Code, Jetbrains IDEs（GoLand, Pycharm, IDEA, WebStorm, Rider, Android Studio, 鸿蒙 IDE 等）, Visual Studio, Vim / NeoVim'),
          },
        ],
      },
    };
  },
};
</script>
