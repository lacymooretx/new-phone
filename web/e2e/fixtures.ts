import { test as base, expect, type Page } from '@playwright/test'
import path from 'path'

// ----- Test credentials (override via env vars) -----
export const TEST_USER = {
  email: process.env.E2E_USER_EMAIL ?? 'admin@example.com',
  password: process.env.E2E_USER_PASSWORD ?? 'password123',
}

export const AUTH_STATE_PATH = path.join(__dirname, '.auth', 'user.json')

// ----- Helper: perform UI login -----
export async function loginViaUI(page: Page, email: string, password: string) {
  await page.goto('/login')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  // Wait for redirect to dashboard
  await expect(page).toHaveURL('/', { timeout: 15_000 })
}

// ----- Helper: perform API login and inject auth state -----
export async function loginViaAPI(page: Page, email: string, password: string) {
  const response = await page.request.post('/api/v1/auth/login', {
    data: { email, password },
  })

  if (!response.ok()) {
    throw new Error(`API login failed: ${response.status()} ${response.statusText()}`)
  }

  const data = await response.json()

  // If MFA is required, fall back to UI login
  if (data.mfa_required) {
    throw new Error('MFA required -- cannot authenticate via API alone; use UI login with MFA handling')
  }

  // Inject tokens into localStorage so the app recognizes the session
  await page.goto('/')
  await page.evaluate((tokens) => {
    localStorage.setItem('refresh_token', tokens.refresh_token)
  }, { access_token: data.access_token, refresh_token: data.refresh_token })

  // Reload so AuthGuard picks up the stored refresh_token
  await page.reload()
  await expect(page).toHaveURL('/', { timeout: 15_000 })
}

// ----- Page Objects -----

export class LoginPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/login')
  }

  get emailInput() {
    return this.page.getByLabel('Email')
  }

  get passwordInput() {
    return this.page.getByLabel('Password')
  }

  get signInButton() {
    return this.page.getByRole('button', { name: 'Sign in' })
  }

  get forgotPasswordLink() {
    return this.page.getByRole('link', { name: /forgot password/i })
  }

  get errorMessage() {
    return this.page.locator('.text-destructive')
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email)
    await this.passwordInput.fill(password)
    await this.signInButton.click()
  }
}

export class SidebarNav {
  constructor(private page: Page) {}

  get root() {
    return this.page.locator('aside')
  }

  get brandLink() {
    return this.root.getByRole('link', { name: 'New Phone' })
  }

  navLink(name: string | RegExp) {
    return this.root.getByRole('link', { name })
  }

  groupLabel(name: string) {
    return this.root.locator('.text-xs.font-semibold', { hasText: name })
  }
}

export class DashboardPO {
  constructor(private page: Page) {}

  get heading() {
    return this.page.getByRole('heading', { name: 'Dashboard' })
  }

  get statCards() {
    // StatCard renders inside a Card component
    return this.page.locator('[class*="card"]').filter({ has: this.page.locator('svg') })
  }

  get quickActionsCard() {
    return this.page.locator('text=Quick Actions').locator('..')
  }

  get recentCallsHeading() {
    return this.page.getByText('Recent Calls')
  }
}

export class DataTablePO {
  constructor(private page: Page) {}

  get searchInput() {
    return this.page.locator('input[placeholder*="Search"]')
  }

  get table() {
    return this.page.locator('table')
  }

  get rows() {
    return this.page.locator('table tbody tr')
  }

  get loadingSkeletons() {
    return this.page.locator('[data-slot="skeleton"]')
  }

  get emptyState() {
    return this.page.locator('table tbody tr td[colspan]')
  }

  get columnsButton() {
    return this.page.getByRole('button', { name: 'Columns' })
  }

  get exportButton() {
    return this.page.getByRole('button', { name: 'Export' })
  }
}

// ----- Custom test fixture that provides page objects -----
type Fixtures = {
  loginPage: LoginPage
  sidebar: SidebarNav
  dashboard: DashboardPO
  dataTable: DataTablePO
}

export const test = base.extend<Fixtures>({
  loginPage: async ({ page }, use) => {
    await use(new LoginPage(page))
  },
  sidebar: async ({ page }, use) => {
    await use(new SidebarNav(page))
  },
  dashboard: async ({ page }, use) => {
    await use(new DashboardPO(page))
  },
  dataTable: async ({ page }, use) => {
    await use(new DataTablePO(page))
  },
})

export { expect }
