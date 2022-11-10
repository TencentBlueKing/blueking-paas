<template lang="html">
    <paas-content-loader :is-loading="loading" :offset-top="0" placeholder="cloud-api-inner-index-loading" :height="300">
        <layout>
            <system-filter
                :list="filterList"
                :type="apiType"
                @on-select="handleSelect"
                @on-refresh="handleRefresh" />
            <div slot="right">
                <render-list
                    :id="curId"
                    :api-type="apiType"
                    :name="curName"
                    :maintainers="maintainers"
                    :is-refresh="isRefresh"
                    @data-ready="handlerDataReady">
                </render-list>
            </div>
        </layout>
    </paas-content-loader>
</template>
<script>
    import Layout from './render-layout';
    import SystemFilter from './system-filter';
    import RenderList from './render-list';
    export default {
        name: '',
        components: {
            Layout,
            SystemFilter,
            RenderList
        },
        props: {
            apiType: {
                type: String,
                default: 'gateway'
            },
            appCode: {
                type: String,
                required: true
            }
        },
        data () {
            return {
                requestQueue: ['filter', 'list'],
                filterList: [],
                curId: '',
                curName: '',
                maintainers: [],
                loading: true,
                isRefresh: false
            };
        },
        computed: {
            isGateway () {
                return this.apiType === 'gateway';
            }
        },
        watch: {
            '$route' () {
                this.requestQueue = ['filter', 'list'];
                this.init();
            },
            requestQueue (value) {
                if (value.length < 1) {
                    this.loading = false;
                    this.$emit('data-ready');
                }
            }
        },
        created () {
            this.init();
        },
        methods: {
            init () {
                this.fetchFilterList();
            },

            handleSelect ({ id, maintainers, name }) {
                this.curId = id;
                this.curName = name;
                this.maintainers = maintainers;
            },

            handleRefresh (data) {
                this.isRefresh = data;
            },

            handlerDataReady () {
                if (this.requestQueue.length > 0) {
                    this.requestQueue.shift();
                }
            },

            async fetchFilterList () {
                const method = this.isGateway ? 'getApis' : 'getSystems';
                try {
                    const res = await this.$store.dispatch(`cloudApi/${method}`, {
                        appCode: this.appCode
                    });
                    this.filterList = Object.freeze(res.data);
                    if (this.filterList.length > 0) {
                        this.curId = this.filterList[0].id;
                        this.curName = this.filterList[0].name;
                        this.maintainers = this.filterList[0].maintainers;
                    }
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.detail || e.message || this.$t('服务暂不可用，请稍后再试')
                    });
                } finally {
                    this.requestQueue.shift();
                }
            }
        }
    };
</script>
