const querystring = require('querystring');
import { bkPagination } from 'BkMagicVue'

const Pagination = {
    extends: bkPagination,
    methods: {
        goto: function (page = 1) {
            let limit = this.realityLimit
            let offset = limit * (page - 1)
            let query = {limit, offset}
            
            let prefix = window.location.href
            if (prefix.indexOf("?") > 0) {
                query = {...querystring.parse(prefix.substr(prefix.indexOf("?") + 1)), ...query}
                prefix = prefix.substr(0, prefix.indexOf("?"))
            }
            query = querystring.stringify(query)
            window.location.href = `${prefix}?${query}`
        }
    },
    created: function (){
        this.$on("change", (page) => {
            this.$bkLoading({title: '加载中'})
            this.$emit("update:current", page)
            this.goto(page)
        })

        this.$on("limit-change", (limit) => {
            this.$bkLoading({title: '加载中'})
            this.$emit("update:current", 1)
            this.realityLimit = limit
            this.goto(1)
        })
    },
}

export default Pagination