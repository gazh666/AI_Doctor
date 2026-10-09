import path from 'node:path';
import { expect, test } from '@playwright/test';
import { bootstrapAuthenticatedSession, mockAuthMe } from './support/session';

test.beforeEach(async ({ page }) => {
  await bootstrapAuthenticatedSession(page);
  await mockAuthMe(page);
});

test('patient triage flow shows diagnosis outcome', async ({ page }) => {
  await page.route('**/api/v1/agents/diagnose', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'OK',
        diagnosis: 'Likely viral upper respiratory infection',
        confidence: 0.88,
        differential_diagnoses: ['Seasonal flu', 'Acute bronchitis'],
        urgency_level: 'ROUTINE',
        final_report: 'Monitor temperature, hydrate, and seek care if worsening.',
        workflow_steps: ['Input validation', 'Agent consensus', 'Plan generation'],
        is_grounded_in_rag: true,
        citations: [
          {
            id: 101,
            rank: 1,
            title: 'WHO respiratory symptom guidance',
            provider: 'medlineplus',
            source: 'https://example.org/who-respiratory',
            excerpt: 'Mild symptoms can be managed with home rest and fluids.',
            similarity: 0.91,
          },
        ],
        treatment_plan: {
          immediate_care: ['Hydration and rest'],
          medications: [
            {
              name: 'Paracetamol',
              dosage: '500mg',
              frequency: 'Every 8 hours',
              duration: '3 days',
              notes: 'Only if fever present',
            },
          ],
          non_pharmacological: ['Warm fluids', 'Rest for 24-48 hours'],
          follow_up: {
            timing: '48 hours',
            what_to_monitor: ['Fever above 101F', 'Breathlessness'],
          },
          red_flags: ['Persistent chest pain'],
          lifestyle_advice: ['Avoid smoke exposure'],
          referral_needed: false,
        },
      }),
    });
  });

  await page.goto('/diagnosis');

  await page.getByLabel('Symptoms *').fill('Fever, sore throat, and mild dry cough for two days');
  await page.getByLabel('Age').fill('34');
  await page.getByLabel('Gender').fill('Female');
  await page.getByLabel('Temperature (°F)').fill('100.2');

  await page.getByRole('button', { name: 'Run Complete Diagnosis' }).click();

  await expect(page.getByText('Primary Diagnosis')).toBeVisible();
  await expect(page.getByText('Likely viral upper respiratory infection')).toBeVisible();
  await expect(page.getByText('Treatment Plan')).toBeVisible();
  await expect(page.getByText('Paracetamol')).toBeVisible();
});

test('voice consult flow connects and renders consultation messages', async ({ page }) => {
  await page.addInitScript(() => {
    class MockWebSocket {
      static OPEN = 1;
      static CLOSED = 3;
      readyState = 0;
      onopen: ((event: Event) => void) | null = null;
      onmessage: ((event: MessageEvent) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;
      onclose: ((event: CloseEvent) => void) | null = null;

      constructor(_url: string) {
        window.setTimeout(() => {
          this.readyState = MockWebSocket.OPEN;
          this.onopen?.(new Event('open'));
        }, 5);
      }

      send(data: string) {
        const payload = JSON.parse(data);
        if (payload.type !== 'auth') {
          return;
        }

        window.setTimeout(() => {
          this.onmessage?.(
            new MessageEvent('message', {
              data: JSON.stringify({ type: 'auth.ok', session_id: 'e2e-session' }),
            })
          );

          this.onmessage?.(
            new MessageEvent('message', {
              data: JSON.stringify({
                type: 'turn.transcript',
                turn_id: 'turn-1',
                transcript: 'I have headache and low fever since yesterday',
                timestamp: new Date().toISOString(),
              }),
            })
          );

          this.onmessage?.(
            new MessageEvent('message', {
              data: JSON.stringify({
                type: 'turn.response',
                turn_id: 'turn-1',
                response_text: 'Hydrate well and monitor symptoms for 24 hours.',
                urgency: 'ROUTINE',
                timestamp: new Date().toISOString(),
              }),
            })
          );
        }, 15);
      }

      close() {
        this.readyState = MockWebSocket.CLOSED;
        this.onclose?.(new CloseEvent('close'));
      }
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (window as any).WebSocket = MockWebSocket;
  });

  await page.goto('/voice');

  await page.getByRole('button', { name: 'Connect Live' }).click();

  await expect(page.getByText('Connected')).toBeVisible();
  await expect(page.getByText('Patient')).toBeVisible();
  await expect(page.getByText('I have headache and low fever since yesterday')).toBeVisible();
  await expect(page.getByText('AI Doctor')).toBeVisible();
  await expect(page.getByText('Hydrate well and monitor symptoms for 24 hours.')).toBeVisible();
});

test('x-ray upload flow returns analysis findings', async ({ page }) => {
  await page.route('**/api/v1/vision/xray/analyze', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        analysis_id: 7001,
        analysis: 'No acute infiltrates',
        findings: ['Mild bilateral perihilar prominence'],
        severity: 'mild',
        confidence: 0.81,
        differential_diagnosis: ['Mild bronchitic changes'],
        recommendations: 'Follow up clinically in 48 hours if symptoms persist.',
        urgent_flags: [],
      }),
    });
  });

  await page.goto('/xray');

  const uploadPath = path.resolve(__dirname, '../public/Chest_X_Ray_Analysis.png');
  await page.locator('#xray-upload').setInputFiles(uploadPath);

  await page.getByLabel('Symptoms (optional)').fill('Persistent dry cough and low fever');
  await page.getByRole('button', { name: 'Analyze X-Ray' }).click();

  await expect(page.getByText('Analysis Results')).toBeVisible();
  await expect(page.getByText('Mild bilateral perihilar prominence')).toBeVisible();
  await expect(page.getByText('MILD')).toBeVisible();
});

test('report export flow downloads patient report', async ({ page }) => {
  await page.route('**/api/v1/exports/diagnoses/csv', async (route) => {
    await route.fulfill({
      status: 200,
      headers: {
        'content-type': 'text/csv',
        'content-disposition': 'attachment; filename="diagnoses.csv"',
      },
      body: 'id,diagnosis,urgency\n1,viral infection,ROUTINE\n',
    });
  });

  await page.goto('/export');

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'Export as CSV' }).click(),
  ]);

  expect(download.suggestedFilename()).toContain('diagnoses.csv');
});
