<template lang="html">
    <div class="right-main">
        <div class="ps-top-bar">
            <h2> {{ $t('代码库管理') }} </h2>
        </div>
        <p v-if="isTips.git && isTips.svn" :class="['ps-tips', localLanguage === 'zh-cn' ? '' : 'ps-tips-en']">{{ $t('支持通过 OAuth 授权拉取 GitHub、 Gitee 代码仓库，可联系管理员设置') }} <a :href="GLOBAL.DOC.OATUH_CONFIG_GUIDE" target="_blank"> {{ $t('配置指引') }} </a></p>
        <paas-content-loader class="ps-container" :is-loading="!gitReady && !svnReady" placeholder="code-loading">
            <git @ready="gitReady = true" @changeTips="changeTips"></git>
            <svn @ready="svnReady = true" @changeTips="changeTips"></svn>
        </paas-content-loader>
    </div>
</template>

<script>
    import svn from './comps/svn.vue';
    import git from './comps/git.vue';

    export default {
        components: {
            git,
            svn
        },
        data () {
            return {
                gitReady: false,
                svnReady: false,
                isTips: {
                    git: false,
                    svn: false
                }
            };
        },
        computed: {
            localLanguage () {
                return this.$store.state.localLanguage;
            }
        },
        methods: {
            changeTips (attribute) {
                this.isTips[attribute] = true;
            }
        }
    };
</script>
