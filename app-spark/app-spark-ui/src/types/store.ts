export interface IUser {
  authenticated: boolean;
  username: string;
  display_name: string;
  tenant_id: string | null;
}
