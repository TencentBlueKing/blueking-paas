<template>
    <div>
        <blueking-user-selector
            class="cmdb-form-objuser"
            ref="userSelector"
            display-list-tips
            v-bind="props"
            v-model="localValue"
            v-if="GLOBAL.USERS_URL"
            @focus="$emit('focus')"
            @blur="$emit('blur')">
        </blueking-user-selector>
        <bk-member-selector
            v-else
            v-model="localValue"
            :max-data="curMaxData"
            ref="member_selector">
        </bk-member-selector>
    </div>
</template>

<script>
    import BluekingUserSelector from '@blueking/user-selector';
    import 'BKSelectMinCss';

    export default {
        name: 'cmdb-form-objuser',
        components: {
            BluekingUserSelector,
            'bk-member-selector': () => {
                return import('./member-selector/member-selector.vue');
            }
        },
        props: {
            value: {
                type: Array,
                default () {
                    return [];
                }
            },
            multiple: {
                type: Boolean,
                default: true
            }
        },
        computed: {
            api () {
                return this.GLOBAL.USERS_URL;
            },
            localValue: {
                get () {
                    return (this.value && this.value.length) ? this.value : [];
                },
                set (val) {
                    this.$emit('input', val);
                    this.$nextTick(() => {
                        this.$emit('change', this.value, val.toString);
                    });
                }
            },
            props () {
                const props = { ...this.$attrs };
                if (this.api) {
                    props.api = this.api;
                } else {
                    props.fuzzySearchMethod = this.fuzzySearchMethod;
                    props.exactSearchMethod = this.exactSearchMethod;
                    props.pasteValidator = this.pasteValidator;
                }
                return props;
            },
            curMaxData () {
                return this.multiple ? -1 : 1;
            }
        },
        methods: {
            focus () {
                this.$refs.userSelector.focus();
            },
            async fuzzySearchMethod (keyword, page = 1) {
                const users = await this.$http.get(`${window.API_HOST}user/list`, {
                    params: {
                        fuzzy_lookups: keyword
                    },
                    config: {
                        cancelPrevious: true
                    }
                });
                return {
                    next: false,
                    results: users.map(user => ({
                        username: user.english_name,
                        display_name: user.chinese_name
                    }))
                };
            },
            exactSearchMethod (usernames) {
                const isBatch = Array.isArray(usernames);
                return Promise.resolve(isBatch ? usernames.map(username => ({ username })) : { username: usernames });
            },
            pasteValidator (usernames) {
                return Promise.resolve(usernames);
            }
        }
    };
</script>

<style lang="scss" scoped>
    .cmdb-form-objuser {
        width: 100%;
    }
</style>
