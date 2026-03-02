import { test as setup, expect } from '@playwright/test'
import { TEST_USER, AUTH_STATE_PATH } from './fixtures'

/**
 * Runs once before all tests to create a shared authenticated session.
 * Saves browser storage state so individual tests don't need to log in.
 */
setup('authenticate', async ({ page }) => {
  await page.goto('/login')

  // Fill login form
  await page.getByLabel('Email').fill(TEST_USER.email)
  await page.getByLabel('Password').fill(TEST_USER.password)
  await page.getByRole('button', { name: 'Sign in' }).click()

  // Wait for successful redirect to dashboard
  await expect(page).toHaveURL('/', { timeout: 15_000 })

  // Persist signed-in state
  await page.context().storageState({ path: AUTH_STATE_PATH })
})
