// -- Permissions (contract C5) ---------------------------------------------
export interface DegreePermission {
  degree_id: string;
  role: "viewer" | "editor";
}

export interface PermissionsPayload {
  degrees: DegreePermission[];
  is_admin: boolean;
}
