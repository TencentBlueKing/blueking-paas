<template lang="html">
  <div class="right-main">
    <paas-content-loader
      class="app-container middle"
      :is-loading="loading"
      placeholder="roles-loading"
    >
      <paas-plugin-title />
      <div class="header mt10 header-flex">
        <!-- v-if="enableToAddRole" -->
        <bk-button
          theme="primary"
          icon="plus"
          @click="createMember"
        >
          {{ $t('新增成员') }}
        </bk-button>
        <bk-input
          v-model="keyword"
          class="search-input"
          :placeholder="$t('请输入')"
          :clearable="true"
          :right-icon="'bk-icon icon-search'"
          @enter="handleSearch"
        />
      </div>
      <!-- <bk-alert type="warning" :show-icon="true">
                <div slot="title">
                    <span class="dev-name">carrielu</span>、
                    <span class="dev-name">v_wmhawang</span>
                    {{ $t('申请成为开发者，前往') }}
                    <span class="detail-doc"> {{ $t('审批') }}</span>
                </div>
            </bk-alert> -->
      <div class="content-wrapper">
        <bk-table
          v-bkloading="{ isLoading: isTableLoading }"
          :data="memberListShow"
          size="small"
          :pagination="pagination"
          :outer-border="false"
          :header-border="false"
          @page-change="pageChange"
          @page-limit-change="limitChange"
        >
          <bk-table-column :label="$t('成员姓名')">
            <template slot-scope="props">
              <span
                v-if="props.row.avatar"
                class="user-photo"
              ><img :src="props.row.avatar"></span>
              <span class="user-name">{{ props.row.username }}</span>
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('角色')">
            <template slot-scope="props">
              <span class="role-name">{{ $t(roleNames[props.row.role.roleName]) }}</span>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('权限')"
            min-width="170"
          >
            <template slot-scope="props">
              <span
                v-for="(perm, permIndex) in roleSpec[props.row.role.roleName]"
                v-if="perm[Object.keys(perm)[0]]"
                :key="permIndex"
                class="ps-pr"
              >
                {{ $t(Object.keys(perm)[0]) }}
              </span>
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('操作')">
            <template slot-scope="props">
              <template v-if="canManageMe(props.row)">
                <bk-button
                  text
                  class="mr5"
                  @click="leaveApp(props.row.role.id, props.row.username)"
                >
                  {{ $t('退出插件') }}
                </bk-button>
              </template>
              <bk-button
                v-if="isChangingRoles(props.row.role)"
                text
                class="mr5"
                @click="updateMember(props.row.role.id, props.row.username, props.row.role.roleName)"
              >
                {{ $t('更换角色') }}
              </bk-button>
              <!-- v-if="canManageMembers(props.row)" -->
              <bk-button
                text
                class="mr5"
                @click="delMember(props.row.username, props.row.role.id)"
              >
                {{ $t('删除成员') }}
              </bk-button>
            </template>
          </bk-table-column>
        </bk-table>
      </div>
    </paas-content-loader>

    <bk-dialog
      v-model="memberMgrConfig.visiable"
      width="540"
      :title="memberMgrConfig.title"
      header-position="left"
      :theme="'primary'"
      :mask-close="false"
      :loading="memberMgrConfig.isLoading"
      @confirm="memberMgrSave"
      @cancel="closeMemberMgrModal"
      @after-leave="hookAfterClose"
    >
      <div
        v-if="memberMgrConfig.showForm"
        style="min-height: 130px;"
      >
        <bk-form
          :label-width="120"
          form-type="vertical"
        >
          <bk-form-item
            :label="$t('成员名称')"
            :required="true"
          >
            <template v-if="memberMgrConfig.userEditable">
              <user v-model="personnelSelectorList" />
              <!-- <bk-member-selector
                                @change="updateValue"
                                v-model="personnelSelectorList"
                                ref="member_selector">
                            </bk-member-selector> -->
            </template>
            <template v-else>
              <bk-input
                v-model="selectedMember.name"
                :readonly="true"
              />
            </template>
          </bk-form-item>
          <bk-form-item
            :label="$t('角色')"
            :required="true"
          >
            <bk-radio-group v-model="roleName">
              <bk-radio
                v-for="(chineseName, name) in roleNames"
                :key="name"
                :value="name"
              >
                {{ $t(chineseName) }}
              </bk-radio>
            </bk-radio-group>
          </bk-form-item>
          <bk-form-item label="">
            <div class="ps-rights-list">
              <!-- roleName 当前权限 -->
              <span class="ps-rights-title">{{ $t('权限列表') }}</span>
              <span
                v-for="(perm, permIndex) in roleSpec[roleName]"
                :key="permIndex"
              >
                <a
                  v-if="perm[Object.keys(perm)[0]]"
                  class="available-right"
                >
                  <span>{{ $t(Object.keys(perm)[0]) }}</span>
                </a>
                <a
                  v-else
                  class="not-available-right"
                >
                  <span>{{ $t(Object.keys(perm)[0]) }}</span>
                </a>
              </span>
            </div>
          </bk-form-item>
        </bk-form>
      </div>
    </bk-dialog>

    <bk-dialog
      v-model="removeUserDialog.visiable"
      width="540"
      :title=" `${$t('删除成员 ')}${selectedMember.name}`"
      :theme="'primary'"
      :mask-close="false"
      :loading="removeUserDialog.isLoading"
      @confirm="delSave"
      @cancel="closeDelModal"
    >
      <div class="tc">
        {{ $t('用户') }} {{ selectedMember.name }} {{ $t('将失去此应用的对应权限，是否确定删除？') }}
      </div>
    </bk-dialog>

    <bk-dialog
      v-model="permissionNoticeDialog.visiable"
      width="540"
      :title="$t('权限须知')"
      :theme="'primary'"
      :mask-close="false"
      :loading="leaveAppDialog.isLoading"
    >
      <div class="tc">
        {{ $t('由于应用目前使用了第三方源码托管系统，当管理员添加新的“开发者”角色用户后，需要同时在源码系统中添加对应的账号权限。否则无法进行正常开发工作') }}
      </div>
      <template slot="footer">
        <bk-button
          theme="primary"
          @click="iKnow"
        >
          {{ $t('我知道了') }}
        </bk-button>
      </template>
    </bk-dialog>
  </div>
</template>

<script>
    import auth from '@/auth';
    import appBaseMixin from '@/mixins/app-base-mixin';
    import user from '@/components/user';
    import i18n from '@/language/i18n.js';
    import paasPluginTitle from '@/components/pass-plugin-title';

    const ROLE_BACKEND_IDS = {
        'administrator': 2,
        'developer': 3
    };

    const ROLE_SPEC_PLUGIN_ZH = {
        '管理员': 'administrator',
        '开发者': 'developer'
    };

    const APP_ROLE_NAMES = {
        'administrator': '管理员',
        'developer': '开发者'
    };

    const ROLE_SPEC_PLUGIN = {
        'administrator': [
            {
                '插件开发': true
            },
            {
                '上线审核': true
            },
            {
                '插件推广': true
            },
            {
                '成员管理': true
            }
        ],
        'developer': [
            {
                '插件开发': true
            },
            {
                '上线审核': false
            },
            {
                '插件推广': true
            },
            {
                '成员管理': false
            }
        ]
    };

    const ROLE_DESC_MAP = {
        'administrator': i18n.t('该角色仅影响用户在“开发者中心”管理该应用的权限，不涉及应用内部权限，请勿混淆')
    };

    export default {
        components: {
            user,
            paasPluginTitle
        },
        mixins: [appBaseMixin],
        data () {
            return {
                currentUser: auth.getCurrentUser().username,
                hasPerm: false,
                loading: true,
                memberList: [],
                memberListShow: [],
                roleNames: APP_ROLE_NAMES,
                roleSpec: ROLE_SPEC_PLUGIN,
                roleKeyZH: ROLE_SPEC_PLUGIN_ZH,
                roleName: 'administrator',
                selectedMember: {
                    id: 0,
                    name: ''
                },
                personnelSelectorList: [],
                memberMgrConfig: {
                    visiable: false,
                    isLoading: false,
                    type: 'create',
                    userEditable: true,
                    title: this.$t('新增成员'),
                    showForm: false
                },
                leaveAppDialog: {
                    visiable: false,
                    isLoading: false
                },
                removeUserDialog: {
                    visiable: false,
                    isLoading: false
                },
                permissionNoticeDialog: {
                    visiable: false
                },

                pagination: {
                    current: 1,
                    count: 0,
                    limit: 10
                },
                currentBackup: 1,
                enableToAddRole: false,
                keyword: '',
                memberListClone: [],
                isTableLoading: false
            };
        },
        computed: {
            currentRoleDesc () {
                return ROLE_DESC_MAP[this.roleName] || '';
            },
            curPluginInfo () {
                return this.$store.state.curPluginInfo;
            },
            pluginInfo () {
                return this.$store.state.pluginInfo;
            },
            pdId () {
                return this.$route.params.pluginTypeId;
            },
            pluginId () {
                return this.$route.params.id;
            }
        },
        watch: {
            '$route' () {
                this.init();
            },
            'pagination.current' (value) {
                this.currentBackup = value;
            },
            keyword (val) {
                if (!val) {
                    this.handleSearch();
                }
            }
        },
        created () {
            this.init();
        },
        methods: {
            pageChange (page) {
                if (this.currentBackup === page) {
                    return;
                }
                this.pagination.current = page;

                this.handleSearch();
                // const start = this.pagination.limit * (this.pagination.current - 1)
                // const end = start + this.pagination.limit
                // this.memberListShow.splice(0, this.memberListShow.length, ...this.memberList.slice(start, end))
            },

            limitChange (currentLimit, prevLimit) {
                this.pagination.limit = currentLimit;
                this.pagination.current = 1;

                this.handleSearch();

                // const start = this.pagination.limit * (this.pagination.current - 1)
                // const end = start + this.pagination.limit
                // this.memberListShow.splice(0, this.memberListShow.length, ...this.memberList.slice(start, end))
            },

            iKnow () {
                this.permissionNoticeDialog.visiable = false;
                !localStorage.getItem('membersNoticeDialogHasShow') && localStorage.setItem('membersNoticeDialogHasShow', true);
            },

            updateValue (curVal) {
                curVal ? this.personnelSelectorList = curVal : this.personnelSelectorList = '';
            },

            init () {
                this.enableToAddRole = this.curAppInfo && this.curAppInfo.role && this.curAppInfo.role.name === 'administrator';
                this.fetchMemberList();
                this.$nextTick(() => {
                    // 如果使用git
                    if (this.curAppDefaultModule.repo && this.curAppDefaultModule.repo.type.indexOf('git') > -1) {
                        if (!localStorage.getItem('membersNoticeDialogHasShow')) {
                            this.permissionNoticeDialog.visiable = true;
                        }
                    }
                });
            },

            async fetchMemberList () {
                this.isTableLoading = true;
                try {
                    const res = await this.$store.dispatch('cloudMembers/getMemberList', { pdId: this.pdId, pluginId: this.pluginId });
                    this.pagination.count = res.length;
                    res.forEach(element => {
                        this.$set(element.role, 'roleName', this.roleKeyZH[element.role.name]);
                    });
                    const start = this.pagination.limit * (this.pagination.current - 1);
                    const end = start + this.pagination.limit;

                    this.hasPerm = true;

                    this.memberList.splice(0, this.memberList.length, ...(res || []));
                    this.memberListShow.splice(0, this.memberListShow.length, ...this.memberList.slice(start, end));
                } catch (e) {
                    this.hasPerm = false;
                    this.$paasMessage({
                        theme: 'error',
                        message: e.detail || this.$t('接口异常')
                    });
                } finally {
                    this.loading = false;
                    this.isTableLoading = false;
                }
            },

            createMember () {
                this.roleName = 'administrator';
                this.personnelSelectorList = [];
                this.memberMgrConfig = {
                    visiable: true,
                    isLoading: false,
                    type: 'create',
                    userEditable: true,
                    title: this.$t('新增成员'),
                    showForm: true
                };
            },

            hookAfterClose () {
                this.memberMgrConfig.showForm = false;
            },

            async createSave () {
                this.memberMgrConfig.isLoading = true;
                if (!this.personnelSelectorList.length) {
                    this.$paasMessage({
                        theme: 'error',
                        message: this.$t('请选择成员！')
                    });
                    setTimeout(() => {
                        this.memberMgrConfig.isLoading = false;
                    }, 100);
                    return;
                }

                let createParam = {};
                const createSuc = [];
                for (let i = 0; i < this.personnelSelectorList.length; i++) {
                    createParam = {
                        'username': this.personnelSelectorList[i],
                        'role': {
                            'id': ROLE_BACKEND_IDS[this.roleName]
                        }
                    };
                    createSuc.push(createParam);
                }
                try {
                    await this.$store.dispatch('cloudMembers/addMember', {
                        pdId: this.pdId,
                        pluginId: this.pluginId,
                        postParams: createSuc
                    });
                    this.closeMemberMgrModal();
                    this.fetchMemberList();
                    this.$paasMessage({
                        theme: 'success',
                        message: this.$t('新增成员成功！')
                    });
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: `${this.$t('添加用户角色失败：')} ${e.detail}`
                    });
                } finally {
                    this.memberMgrConfig.isLoading = false;
                }
            },

            leaveApp (delMemberID, delMemberName) {
                this.selectedMember.id = delMemberID;
                this.selectedMember.name = delMemberName;
                this.$bkInfo({
                    title: `退出并放弃此插件的对应权限，是否确定？`,
                    width: 480,
                    maskClose: true,
                    confirmFn: () => {
                        this.leaveSave();
                    }
                });
            },

            // 退出插件
            async leaveSave () {
                try {
                    await this.$store.dispatch('cloudMembers/quitApplication', { pdId: this.pdId, pluginId: this.pluginId });
                    // 退出插件跳转
                    this.$router.push({
                        path: '/'
                    });
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: `${this.$t('退出插件失败：')} ${e.detail}`
                    });
                } finally {
                    this.leaveAppDialog.isLoading = false;
                }
            },

            updateMember (updateMemberID, updateMemberName, updateMemberRole) {
                this.selectedMember.id = updateMemberID;
                this.selectedMember.name = updateMemberName;
                this.roleName = updateMemberRole;
                this.memberMgrConfig = {
                    visiable: true,
                    isLoading: false,
                    type: 'edit',
                    userEditable: false,
                    title: this.$t('更换角色'),
                    showForm: true
                };
            },

            memberMgrSave () {
                const mgrType = this.memberMgrConfig.type;
                if (mgrType === 'edit') {
                    return this.updateSave();
                } else if (mgrType === 'create') {
                    return this.createSave();
                }
            },

            // 是否更新接口
            async updateSave () {
                const updateParam = [
                    {
                        'username': this.selectedMember.name,
                        'role': {
                            'id': ROLE_BACKEND_IDS[this.roleName]
                        }
                    }
                ];
                this.memberMgrConfig.isLoading = true;
                try {
                    // 复用新建接口
                    await this.$store.dispatch('cloudMembers/addMember', {
                        pdId: this.pdId,
                        pluginId: this.pluginId,
                        postParams: updateParam
                    });
                    this.closeMemberMgrModal();
                    this.fetchMemberList();
                    this.$paasMessage({
                        theme: 'success',
                        message: this.$t('角色更新成功！')
                    });
                    // if (this.selectedMember.name === this.currentUser && this.roleName !== 'administrator') {
                    //     this.enableToAddRole = false;
                    // }
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: `${this.$t('修改角色失败：')} ${e.detail}`
                    });
                } finally {
                    this.memberMgrConfig.isLoading = false;
                }
            },

            delMember (delMemberName, delMemberID) {
                this.selectedMember.id = delMemberID;
                this.selectedMember.name = delMemberName;
                this.removeUserDialog.visiable = true;
            },

            async delSave () {
                try {
                    await this.$store.dispatch('cloudMembers/deleteRole', {
                        pdId: this.pdId,
                        pluginId: this.pluginId,
                        username: this.selectedMember.name
                    });
                    this.closeDelModal();
                    this.$paasMessage({
                        theme: 'success',
                        message: this.$t('删除成员成功！')
                    });
                    this.fetchMemberList();
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: `${this.$t('删除成员失败：')} ${e.detail}`
                    });
                }
            },

            closeDelModal () {
                this.removeUserDialog.visiable = false;
            },

            closeMemberMgrModal () {
                this.memberMgrConfig.visiable = false;
            },

            // 是否显示退出插件
            canManageMe (roleInfo) {
                if (roleInfo.username !== this.currentUser) {
                    return false;
                }
                // if (roleInfo.user.id === this.curAppInfo.applicatio && this.curAppInfo.application.owner) {
                //     return false;
                // }
                return true;
            },

            isChangingRoles (roleInfo) {
                if (roleInfo.roleName === 'developer') {
                    return false;
                }
                return true;
            },

            canManageMembers (roleInfo) {
                if (roleInfo.username === this.currentUser || !this.enableToAddRole) {
                    // 不能操作自身角色 || 非管理员不能操作角色管理
                    return false;
                }
                return true;
            },

            canChangeMembers () {
                if (!this.enableToAddRole) {
                    return false;
                }
                return true;
            },
            handleSearch () {
                if (this.keyword) {
                    this.memberListShow = this.memberList.filter(apigw => {
                        return apigw.username.toLowerCase().indexOf(this.keyword.toLowerCase()) > -1;
                    });
                    this.memberListClone = [...this.memberListShow];
                    this.pagination.count = this.memberListClone.length;
                    if (this.memberListClone.length > 10) {
                        const start = this.pagination.limit * (this.pagination.current - 1);
                        const end = start + this.pagination.limit;
                        this.memberListShow.splice(0, this.memberListShow.length, ...this.memberListClone.slice(start, end));
                    }
                } else {
                    this.fetchMemberList();
                }
            }
        }
    };
</script>

<style lang="scss" scoped>
    .content-wrapper {
        margin-top: 16px;
    }
    .search-input {
         width: 360px;
         display: inline-block;
    }
    .user-photo {
        margin: 5px 0;
        display: inline-block;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        overflow: hidden;
        border: solid 1px #eaeaea;
        vertical-align: middle;

        img {
            width: 100%;
            height: 100%;
        }
    }

    .user-name {
        display: inline-block;
        padding-left: 10px;
        font-size: 14px;
        color: #63656E;
        vertical-align: middle;
    }
    .role-name {
        color: #63656E;
    }

    .ps-pr {
        padding-right: 15px;
        color: #63656E;
    }

    .middle {
        padding-top: 15px;
    }

    .ps-rights-list {
        height: 54px;
        line-height: 54px;
        background: #F5F7FA;
        padding-left: 24px;
        border-radius: 2px;

        .ps-rights-title {
            font-size: 14px;
            margin-right: 16px;
            color: #63656E;
        }

        a {
            margin-right: 7px;
            padding: 4px 8px;
            font-size: 12px;
            line-height: 1;
            color: #666;
            cursor: default;

            &.available-right {
                border: 1px solid rgba(58,132,255,0.30);
                background: #EDF4FF;
                color: #3A84FF;

                i {
                    color: #3A84FF;
                    transform: scale(.95);
                }
            }

            &.not-available-right {
                border: 1px solid #ddd;
                background: #FAFBFD;
                color: #ddd;

                i {
                    transform: scale(.75);
                }
            }

            i {
                display: inline-block;
                margin-left: 3px;
            }
        }
    }

    .header-flex {
        display: flex;
        justify-content: space-between;
        margin-bottom: 16px;
    }

    .detail-doc {
        color: #3A84FF;
        cursor: pointer;
    }

    .dev-name {
        font-weight: 700;
    }
</style>
