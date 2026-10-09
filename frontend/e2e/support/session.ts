import { Page } from '@playwright/test';

const AUTH_COOKIE_NAME = 'rural_ai_auth';

export async function bootstrapAuthenticatedSession(page: Page): Promise<void> {
  await page.context().addCookies([
    {
      name: AUTH_COOKIE_NAME,
      value: '1',
      domain: '127.0.0.1',
      path: '/',
      httpOnly: false,
      secure: false,
      sameSite: 'Lax',
    },
  ]);

  await page.addInitScript(() => {
    window.localStorage.setItem('access_token', 'e2e-access-token');
  });
}

export async function mockAuthMe(page: Page): Promise<void> {
  await page.route('**/api/v1/auth/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 1,
        email: 'e2e.user@ruralai.test',
        full_name: 'E2E Rural Clinician',
        role: 'doctor',
        is_active: true,
        created_at: '2026-01-01T00:00:00Z',
      }),
    });
  });
}
