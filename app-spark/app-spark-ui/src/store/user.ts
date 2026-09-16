import { defineStore } from 'pinia';
import type { IUser } from 'types/store';

export const useUser = defineStore('user', {
  state: () => ({
    user: {
      authenticated: false,
      username: '',
      display_name: '',
      tenant_id: null,
    },
  }),
  actions: {
    setUser(user: IUser) {
      this.user = user;
    },
  },
});
