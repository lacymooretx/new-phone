import { test, expect, LoginPage, TEST_USER } from './fixtures'

// Login tests do NOT use pre-authenticated state -- they test the login flow itself.
test.use({ storageState: { cookies: [], origins: [] } })

test.describe('Login page', () => {
  let loginPage: LoginPage

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page)
    await loginPage.goto()
  })

  test('shows login form with email and password fields', async ({ page }) => {
    // Heading: app name
    await expect(page.getByText('New Phone')).toBeVisible()
    await expect(page.getByText('Sign in to your account')).toBeVisible()

    // Form fields
    await expect(loginPage.emailInput).toBeVisible()
    await expect(loginPage.emailInput).toHaveAttribute('type', 'email')
    await expect(loginPage.emailInput).toHaveAttribute('placeholder', 'admin@example.com')

    await expect(loginPage.passwordInput).toBeVisible()
    await expect(loginPage.passwordInput).toHaveAttribute('type', 'password')

    // Sign in button
    await expect(loginPage.signInButton).toBeVisible()
    await expect(loginPage.signInButton).toBeEnabled()

    // Forgot password link
    await expect(loginPage.forgotPasswordLink).toBeVisible()
    await expect(loginPage.forgotPasswordLink).toHaveAttribute('href', '/forgot-password')
  })

  test('displays error for invalid credentials', async ({ page: _page }) => {
    await loginPage.login('bad@example.com', 'wrong-password')

    // Wait for error message to appear
    await expect(loginPage.errorMessage).toBeVisible({ timeout: 10_000 })
    // The error text will be "Login failed" or a server-provided detail
    await expect(loginPage.errorMessage).toHaveText(/.+/)
  })

  test('successfully logs in with valid credentials and redirects to dashboard', async ({ page }) => {
    await loginPage.login(TEST_USER.email, TEST_USER.password)

    // Should redirect to the dashboard (root route)
    await expect(page).toHaveURL('/', { timeout: 15_000 })

    // Dashboard heading should be visible
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  })

  test('shows MFA prompt when MFA is required', async ({ page }) => {
    // This test uses route interception to simulate a MFA-required response
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          mfa_required: true,
          mfa_token: 'test-mfa-token-123',
        }),
      })
    })

    await loginPage.login(TEST_USER.email, TEST_USER.password)

    // MFA form should appear with a code input
    await expect(page.getByLabel('Authentication Code')).toBeVisible({ timeout: 5_000 })
    await expect(page.getByRole('button', { name: 'Verify' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Back to login' })).toBeVisible()

    // Verify button should be disabled until 6-digit code entered
    await expect(page.getByRole('button', { name: 'Verify' })).toBeDisabled()

    // Enter a 6-digit code
    await page.getByLabel('Authentication Code').fill('123456')
    await expect(page.getByRole('button', { name: 'Verify' })).toBeEnabled()

    // Click "Back to login" to return to the login form
    await page.getByRole('button', { name: 'Back to login' }).click()
    await expect(loginPage.emailInput).toBeVisible()
  })

  test('redirects to login when accessing protected route unauthenticated', async ({ page }) => {
    // Try to navigate to a protected route directly
    await page.goto('/extensions')

    // AuthGuard should redirect to /login
    await expect(page).toHaveURL('/login', { timeout: 15_000 })
  })

  test('logout clears session and redirects to login', async ({ page }) => {
    // First, log in
    await loginPage.login(TEST_USER.email, TEST_USER.password)
    await expect(page).toHaveURL('/', { timeout: 15_000 })

    // Open the user dropdown in the header
    await page.locator('header').getByRole('button').filter({ has: page.locator('span') }).last().click()

    // Click "Log out"
    await page.getByRole('menuitem', { name: 'Log out' }).click()

    // Should redirect to login
    await expect(page).toHaveURL('/login', { timeout: 10_000 })

    // Verify we can't access protected routes
    await page.goto('/extensions')
    await expect(page).toHaveURL('/login', { timeout: 10_000 })
  })
})
