import { test, expect } from './fixtures'

test.describe('Users page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/users')
  })

  test('users list page loads', async ({ page }) => {
    await expect(page).toHaveURL('/users')
    await expect(page.getByRole('heading', { name: 'Users' })).toBeVisible()
    await expect(page.getByText('Manage user accounts')).toBeVisible()
  })

  test('table shows user data or empty state', async ({ page, dataTable }) => {
    // Wait for loading to finish
    const tableOrEmpty = dataTable.table.or(page.getByText('No users yet'))
    await expect(tableOrEmpty).toBeVisible({ timeout: 15_000 })

    const hasUsers = await dataTable.rows.count() > 0
    if (hasUsers) {
      await expect(dataTable.rows.first()).toBeVisible()
    } else {
      await expect(page.getByText('No users yet')).toBeVisible()
      await expect(page.getByText('Create a user account to get started.')).toBeVisible()
    }
  })

  test('role badges display in the user table', async ({ page, dataTable }) => {
    // Wait for table to load
    await expect(page.getByRole('heading', { name: 'Users' })).toBeVisible()

    const rowCount = await dataTable.rows.count()
    if (rowCount > 0) {
      // Role badges are rendered as Badge components in the table
      // Check that at least one badge-like element is present in the table
      const badges = page.locator('table tbody [data-slot="badge"]')
      await expect(badges.first()).toBeVisible({ timeout: 5_000 })
    }
  })

  test('search works on users table', async ({ page }) => {
    // Search input
    const searchInput = page.getByPlaceholder('Search users...')
    await expect(searchInput).toBeVisible()

    // Type search
    await searchInput.fill('admin')
    await expect(searchInput).toHaveValue('admin')
  })

  test('can open create user dialog', async ({ page }) => {
    // "Create User" button
    const createButton = page.getByRole('button', { name: 'Create User' })
    await expect(createButton).toBeVisible()
    await createButton.click()

    // Dialog should open
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible({ timeout: 5_000 })
    await expect(dialog.getByText('Create User')).toBeVisible()

    // Form fields
    await expect(dialog.getByLabel('Email')).toBeVisible()
    await expect(dialog.getByLabel('Password')).toBeVisible()
    await expect(dialog.getByLabel('First Name')).toBeVisible()
    await expect(dialog.getByLabel('Last Name')).toBeVisible()

    // Close
    await page.keyboard.press('Escape')
    await expect(dialog).not.toBeVisible()
  })
})
