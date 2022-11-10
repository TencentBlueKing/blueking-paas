<template lang="html">
    <div class="container biz-create-success">
        <div class="ps-top-bar">
            <div class="header-title">
                <span class="app-code">{{ curAppCode }}</span>
                <i class="paasng-icon paasng-angle-down arrows"></i>
                <!-- <span class="arrows">></span> -->
                {{ $t('镜像凭证') }}
            </div>
        </div>
        <paas-content-loader class="app-container" :is-loading="isLoading" placeholder="roles-loading">
            <div class="app-container middle ps-main">
                <bk-button
                    theme="primary"
                    class="mb15"
                    @click="handleVoucher">
                    <i class="paasng-icon paasng-plus mr5"></i> {{ $t('新增凭证') }}
                </bk-button>
                <bk-table
                    :data="voucherList"
                    size="small"
                    :pagination="pagination"
                    v-bkloading="{ isLoading: tableLoading, opacity: 1 }"
                    @page-change="pageChange"
                    @page-limit-change="limitChange">
                    <bk-table-column :label="$t('名称')">
                        <template slot-scope="props">
                            {{ props.row.name || '--' }}
                        </template>
                    </bk-table-column>
                    <bk-table-column :label="$t('账号')">
                        <template slot-scope="props">
                            {{ props.row.username || '--' }}
                        </template>
                    </bk-table-column>
                    <bk-table-column :label="$t('密码')">
                        <span>******</span>
                    </bk-table-column>
                    <bk-table-column :label="$t('描述')">
                        <template slot-scope="props">
                            {{ props.row.description || '--' }}
                        </template>
                    </bk-table-column>
                    <bk-table-column width="120" :label="$t('操作')">
                        <template slot-scope="props">
                            <bk-button
                                class="mr10"
                                text
                                theme="primary"
                                @click="handleEdit(props.row)">
                                {{ $t('编辑') }}
                            </bk-button>
                            <bk-button
                                class="mr10"
                                text
                                theme="primary"
                                @click="handleDelete(props.row)">
                                {{ $t('删除') }}
                            </bk-button>
                        </template>
                    </bk-table-column>
                </bk-table>
            </div>
        </paas-content-loader>
        <create-voucher
            ref="voucherDialog"
            :config="visiableDialogConfig"
            :type="type"
            :voucher-detail="voucherDetail"
            @updata="updateVoucher"
            @confirm="addVoucher"
            @close="isCreateVoucher">
        </create-voucher>
    </div>
</template>

<script>
    import i18n from '@/language/i18n.js';
    import _ from 'lodash';
    import CreateVoucher from './create-voucher.vue';
    export default {
        components: {
            CreateVoucher
        },
        data () {
            return {
                voucherList: [],
                pagination: {
                    current: 1,
                    count: 0,
                    limit: 10
                },
                visiableDialogConfig: {
                    visiable: false,
                    loading: false,
                    title: i18n.t('新增凭证')
                },
                isLoading: true,
                visiableDialog: false,
                tableLoading: false,
                type: 'new',
                voucherDetail: {}
            };
        },
        computed: {
            appCode () {
                return this.$route.params.id;
            },
            curAppCode () {
                return this.$store.state.curAppCode;
            }
        },
        watch: {
            curAppCode () {
                this.getVoucherList();
                this.isLoading = true;
            }
        },
        created () {
            this.init();
        },
        methods: {
            init () {
                this.getVoucherList();
            },

            // 获取凭证列表
            async getVoucherList () {
                this.tableLoading = true;
                try {
                    const appCode = this.appCode;
                    const res = await this.$store.dispatch('voucher/getVoucherList', { appCode });
                    this.voucherList = res;
                    this.voucherList.forEach(item => {
                        item.password = '';
                    });
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.detail || this.$t('接口异常')
                    });
                } finally {
                    this.tableLoading = false;
                    setTimeout(() => {
                        this.isLoading = false;
                    }, 500);
                }
            },
            
            async addVoucher (formData) {
                this.visiableDialogConfig.loading = true;
                const appCode = this.appCode;
                const data = formData;
                try {
                    await this.$store.dispatch('voucher/addVoucher', { appCode, data });
                    this.$paasMessage({
                        theme: 'success',
                        message: this.$t('添加成功')
                    });
                    this.$refs.voucherDialog.handleCancel();
                    this.getVoucherList();
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.detail || this.$t('接口异常')
                    });
                } finally {
                    this.visiableDialogConfig.loading = false;
                }
            },

            async updateVoucher (formData) {
                const appCode = this.appCode;
                const voucherName = formData.name;
                const data = formData;
                try {
                    await this.$store.dispatch('voucher/updateVoucher', { appCode, voucherName, data });
                    this.$paasMessage({
                        theme: 'success',
                        message: this.$t('更新成功')
                    });
                    this.$refs.voucherDialog.handleCancel();
                    this.getVoucherList();
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.detail || this.$t('接口异常')
                    });
                }
            },

            async deleteVoucher (name) {
                const appCode = this.appCode;
                const voucherName = name;
                try {
                    await this.$store.dispatch('voucher/deleteVoucher', { appCode, voucherName });
                    this.$paasMessage({
                        theme: 'success',
                        message: this.$t('删除成功')
                    });
                    this.visiableDialogConfig.visiable = false;
                    this.getVoucherList();
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.detail || this.$t('接口异常')
                    });
                }
            },

            // 新增凭证
            handleVoucher () {
                this.visiableDialogConfig.visiable = true;
                this.visiableDialogConfig.title = this.$t('新增凭证');
                this.type = 'new';
                this.voucherDetail = {};
            },

            // 编辑凭证
            handleEdit (data) {
                this.visiableDialogConfig.visiable = true;
                this.visiableDialogConfig.title = this.$t('编辑凭证');
                this.type = 'edit';
                this.voucherDetail = _.cloneDeep(data);
            },

            pageChange (page) {
                if (this.currentBackup === page) {
                    return;
                }
                this.pagination.current = page;
            },

            limitChange (currentLimit, prevLimit) {
                this.pagination.limit = currentLimit;
                this.pagination.current = 1;
            },

            handleDelete (data) {
                this.$bkInfo({
                    extCls: 'delete-voucher',
                    title: this.$t('确认删除镜像凭证：') + data.name,
                    subTitle: this.$t('删除凭证后，使用该凭证的镜像将无法部署'),
                    confirmFn: () => {
                        this.deleteVoucher(data.name);
                    }
                });
                this.$nextTick(() => {
                    this.addTitle(data.name);
                });
            },

            isCreateVoucher (data) {
                this.visiableDialogConfig.visiable = false;
                this.visiableDialog = false;
            },

            addTitle (name) {
                document.querySelector('.delete-voucher .bk-dialog-header-inner').setAttribute('title', name);
            }
        }
    };
</script>

<style lang="scss" scoped>

    .ps-main {
        margin-top: 15px;
    }
    .header-title {
        display: flex;
        align-items: center;
        .app-code {
            color: #979BA5;
        }
        .arrows {
            margin: 0 9px;
            transform: rotate(-90deg);
            font-size: 12px;
            font-weight: 600;
            color: #979ba5;
        }
    }
</style>
