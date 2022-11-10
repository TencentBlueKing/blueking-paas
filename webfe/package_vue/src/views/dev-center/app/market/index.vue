<template>
    <div class="right-main">
        <div class="ps-top-bar">
            <h2> {{ $t('应用市场') }} </h2>
        </div>
        <paas-content-loader :is-loading="isDataLoading" placeholder="market-loading" :offset-top="25" class="app-container overview-middle">
            <section v-show="!isDataLoading">
                <bk-tab class="mt5"
                    :active.sync="active"
                    type="unborder-card"
                    ext-cls="mark-info-tab-cls"
                    @tab-change="handleTabChange">
                    <bk-tab-panel name="visitInfo" :label="$t('发布管理')">
                    </bk-tab-panel>
                    <bk-tab-panel name="baseInfo" :label="$t('修改市场信息')">
                    </bk-tab-panel>
                </bk-tab>

                <paas-content-loader :is-loading="infoTabLoading || visitTabLoading" :placeholder="loaderPlaceholder" :height="785">
                    <template v-if="active === 'visitInfo'">
                        <market-info class="mt25" :key="comKey" @data-ready="handleDataReady"></market-info>
                    </template>
                    <template v-else>
                        <market-manager class="mt25" :key="comKey" @data-ready="handleDataReady"></market-manager>
                    </template>
                </paas-content-loader>
            </section>
        </paas-content-loader>
    </div>
</template>

<script>
    import MarketInfo from './market-info';
    import MarketManager from './market-manager';

    export default {
        components: {
            MarketInfo,
            MarketManager
        },
        data () {
            return {
                active: '',
                isDataLoading: true,
                infoTabLoading: false,
                visitTabLoading: false,
                comKey: -1
            };
        },
        computed: {
            loaderPlaceholder () {
                return this.active === 'visitInfo' ? 'market-visit-loading' : 'market-info-loading';
            }
        },
        watch: {
            '$route' () {
                this.init();
            }
        },
        provide () {
            return {
                changeTab: this.handleTabChange
            };
        },
        created () {
            this.init();
        },
        methods: {
            init () {
                // 如果有query，根据query展示相应tab
                const autoFocus = this.$route.query.focus;
                if (autoFocus && autoFocus === 'baseInfo') {
                    this.active = 'baseInfo';
                } else {
                    this.active = 'visitInfo';
                }

                this.comKey = +new Date();
            },
            async handleTabChange (name) {
                this.active = name;
                if (name === 'baseInfo') {
                    this.infoTabLoading = true;
                } else {
                    this.visitTabLoading = true;
                }

                this.comKey = +new Date();
            },

            handleDataReady () {
                this.isDataLoading = false;
                this.infoTabLoading = false;
                this.visitTabLoading = false;
            }
        }
    };
</script>

<style lang="scss" scoped>
    @import 'index.scss';
</style>
