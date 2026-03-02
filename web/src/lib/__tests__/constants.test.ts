import { describe, it, expect } from "vitest"
import { hasPermission, isMspRole, PERMISSIONS } from "../constants"

describe("hasPermission()", () => {
  it("msp_super_admin has all permissions", () => {
    for (const perm of Object.values(PERMISSIONS)) {
      expect(hasPermission("msp_super_admin", perm)).toBe(true)
    }
  })

  it("tenant_user has view_own_profile", () => {
    expect(hasPermission("tenant_user", PERMISSIONS.VIEW_OWN_PROFILE)).toBe(true)
  })

  it("tenant_user does NOT have manage_platform", () => {
    expect(hasPermission("tenant_user", PERMISSIONS.MANAGE_PLATFORM)).toBe(false)
  })

  it("msp_tech does NOT have manage_platform", () => {
    expect(hasPermission("msp_tech", PERMISSIONS.MANAGE_PLATFORM)).toBe(false)
  })

  it("tenant_admin has manage_extensions", () => {
    expect(hasPermission("tenant_admin", PERMISSIONS.MANAGE_EXTENSIONS)).toBe(true)
  })
})

describe("isMspRole()", () => {
  it("returns true for msp_super_admin", () => {
    expect(isMspRole("msp_super_admin")).toBe(true)
  })

  it("returns true for msp_tech", () => {
    expect(isMspRole("msp_tech")).toBe(true)
  })

  it("returns false for tenant_admin", () => {
    expect(isMspRole("tenant_admin")).toBe(false)
  })

  it("returns false for tenant_user", () => {
    expect(isMspRole("tenant_user")).toBe(false)
  })
})
