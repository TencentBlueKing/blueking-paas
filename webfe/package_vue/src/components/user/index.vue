<template>
  <div>
    <blueking-user-selector
      v-if="GLOBAL.USERS_URL"
      ref="userSelector"
      v-model="localValue"
      class="cmdb-form-objuser"
      display-list-tips
      v-bind="props"
      @focus="$emit('focus')"
      @blur="$emit('blur')"
    />
    <bk-member-selector
      v-else
      ref="member_selector"
      v-model="localValue"
      :max-data="curMaxData"
    />
  </div>
</template>

<script>
    import BluekingUserSelector from '@blueking/user-selector';
    // import 'BKSelectMinCss';

    export default {
        name: 'CmdbFormObjuser',
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
                if (this.$refs.userSelector) {
                    this.$refs.userSelector.focus();
                } else if (this.$refs.member_selector) {
                    this.$refs.member_selector.$el.click();
                }
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
