<template lang="html">
    <div class="right-main">
        <div class="ps-top-bar">
            <h2 v-if="categoryId === 1"> {{ $t('数据存储') }} </h2>
            <h2 v-else-if="categoryId === 2"> {{ $t('健康监测') }} </h2>
        </div>
        <div class="ps-container service">
            <paas-content-loader class="middle bnone" :is-loading="isLoading" placeholder="service-loading" :offset-top="15">
                <div class="bk-button-group pt15" v-if="!isEmpty && uniqueRegionList.length > 1">
                    <bk-button
                        style="width: 130px;"
                        theme="primary"
                        :outline="tabActive !== 'all'"
                        @click="tabActive = 'all'">
                        {{ $t('全部') }}
                    </bk-button>
                    <bk-button
                        v-for="(item, index) in categoryObject"
                        :key="index"
                        style="width: 130px;"
                        theme="primary"
                        :outline="tabActive !== index"
                        @click="tabChange(index)"
                        v-if="index !== 'all'">
                        {{lauguageMap[index]}}
                    </bk-button>
                </div>

                <div class="category-list">
                    <ul class="service-list" v-if="categoryObject[tabActive] && categoryObject[tabActive].services && categoryObject[tabActive].services.length">
                        <li v-for="(service, index) in categoryObject[tabActive].services" :key="index">
                            <router-link :to="{ name: 'serviceInnerPage', params: { category_id: categoryId, name: service.name } }">
                                <img v-bind:src="service.logo" class="service-list-img" alt="">
                                <span class="service-list-tit">{{service.display_name}}</span>
                                <span class="service-list-con">{{service.description}}</span>
                            </router-link>
                        </li>
                    </ul>
                </div>

                <div v-if="isEmpty" style="height: 250px;">
                    <div class="ps-no-result text">
                        <p><i class="paasng-icon paasng-empty"></i></p>
                        <p> {{ $t('暂无增强服务') }} </p>
                    </div>
                </div>
            </paas-content-loader>
        </div>
    </div>
</template>

<script>
    export default {
        data () {
            return {
                isLoading: false,
                categoryId: '',

                lauguageMap: {
                    all: this.$t('全部'),
                    ieod: this.$t('内部版'),
                    tencent: this.$t('外部版'),
                    clouds: this.$t('混合云版')
                },

                tabActive: 'all',

                categoryObject: {
                    all: {
                        services: []
                    }
                },
                uniqueRegionList: []
            };
        },
        computed: {
            isEmpty () {
                const keys = Object.keys(this.categoryObject);
                return keys.every(item => !this.categoryObject[item].services.length);
            }
        },
        watch: {
            '$route' () {
                this.categoryId = Number(this.$route.params.category_id);
                this.tabActive = 'all';
                this.categoryObject = Object.assign({}, {
                    all: {
                        services: []
                    }
                });
                this.fetchCategoryInfo();
            }
        },
        async created () {
            this.categoryId = Number(this.$route.params.category_id);
            this.fetchCategoryInfo();
        },
        methods: {
            tabChange (tab) {
                this.tabActive = tab;
                const tempServices = [];
                this.categoryObject.all.services.forEach(item => {
                    if (item.enabled_regions.includes(tab)) {
                        tempServices.push(item);
                    }
                });

                this.categoryObject[tab].services = [...tempServices];
            },
            fetchCategoryInfo () {
                this.isLoading = true;
                this.$http.get(`${BACKEND_URL}/api/services/categories/${this.categoryId}/`).then((response) => {
                    const resData = response;

                    const allRegions = []

                    ;(resData.results || []).forEach(item => {
                        item.enabled_regions.forEach(regItem => {
                            allRegions.push(regItem);
                        });
                    });

                    this.uniqueRegionList = [...new Set(allRegions)];

                    this.uniqueRegionList.forEach(item => {
                        this.$set(this.categoryObject, item, {
                            services: []
                        });
                    });

                    this.categoryObject.all.services = [...resData.results];

                    this.isLoading = false;
                });
            }
        }
    };
</script>

<style lang="scss" scoped>
    .category-list {
        margin-top: 20px;
    }

    .service-list {
        margin: 0 -6px 0 -6px;
        overflow: hidden;
    }

    .service-list li {
        position: relative;
        padding: 0 6px 12px 6px;
        width: 25%;
        float: left;
    }

    .service-list li.on,
    .service-list li:hover {
        a {
            border: solid 1px #3A84FF;
            box-shadow: 0 0 1px #5cadff;
        }
    }

    .service-list li a {
        width: 100%;
        display: block;
        height: 168px;
        border: solid 1px #e6e9ea;
        border-radius: 2px;
        text-align: center;
        transition: all .5s;
    }

    .service-list-img {
        display: block;
        margin: 24px auto auto auto;
        height: 48px;
    }

    .service-list-tit {
        display: block;
        padding: 10px 0;
        height: 34px;
        line-height: 34px;
        font-weight: bold;
        color: #5d6075;
        overflow: hidden;
    }

    .service-list-con {
        display: block;
        padding: 0 15px;
        height: 40px;
        line-height: 20px;
        color: #666;
        font-size: 12px;
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
    }
</style>
