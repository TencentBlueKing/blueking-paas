<template>
    <div>
        <blueking-user-selector
            ref="user_selector"
            display-list-tips
            style="width: 100%"
            v-bind="props"
            v-model="localValue"
            v-if="GLOBAL_CONFIG.LIST_USERS_API"
            @focus="$emit('focus')"
            @blur="$emit('blur')">
        </blueking-user-selector>
        <bk-member-selector
            v-else
            v-model="localValue"
            ref="member_selector">
        </bk-member-selector>
    </div>
</template>

<script>
    import BluekingUserSelector from 'Extension/@blueking/user-selector'
    export default {
        name: 'cmdb-form-objuser',
        components: {
            BluekingUserSelector
        },
        props: {
            value: {
                type: Array,
                default () {
                    return []
                }
            }
        },
        computed: {
            api () {
                return this.GLOBAL_CONFIG.LIST_USERS_API
            },
            localValue: {
                get () {
                    return (this.value && this.value.length) ? this.value : []
                },
                set (val) {
                    this.$emit('input', val)
                    this.$nextTick(() => {
                        this.$emit('change', this.value, val.toString)
                    })
                }
            },
            props () {
                const props = { ...this.$attrs }
                if (this.api) {
                    props.api = this.api
                } else {
                    props.fuzzySearchMethod = this.fuzzySearchMethod
                    props.exactSearchMethod = this.exactSearchMethod
                    props.pasteValidator = this.pasteValidator
                }
                return props
            }
        },
        methods: {
            focus () {
                this.$refs.userSelector.focus()
            },
            async fuzzySearchMethod (keyword, page = 1) {
                const users = await this.$http.get(`${window.API_HOST}user/list`, {
                    params: {
                        fuzzy_lookups: keyword
                    },
                    config: {
                        cancelPrevious: true
                    }
                })
                return {
                    next: false,
                    results: users.map(user => ({
                        username: user.english_name,
                        display_name: user.chinese_name
                    }))
                }
            },
            exactSearchMethod (usernames) {
                const isBatch = Array.isArray(usernames)
                return Promise.resolve(isBatch ? usernames.map(username => ({ username })) : { username: usernames })
            },
            pasteValidator (usernames) {
                return Promise.resolve(usernames)
            }
        }
    }
</script>

<style scoped>

</style>
