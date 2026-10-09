import { act, renderHook, waitFor } from '@testing-library/react';
import { useLiveVoiceConsultation } from '@/hooks/useLiveVoiceConsultation';

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  static OPEN = 1;
  static CLOSED = 3;

  readyState = 0;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;
  sent: string[] = [];
  url: string;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send(payload: string) {
    this.sent.push(payload);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.();
  }

  open() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.();
  }

  emit(payload: unknown) {
    this.onmessage?.({ data: JSON.stringify(payload) });
  }
}

describe('useLiveVoiceConsultation', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    MockWebSocket.instances = [];
    Object.defineProperty(global, 'WebSocket', {
      writable: true,
      value: MockWebSocket,
    });
    localStorage.setItem('access_token', 'token-abc');
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
    localStorage.removeItem('access_token');
  });

  it('reconnects after an unexpected disconnect', async () => {
    const { result } = renderHook(() => useLiveVoiceConsultation());

    act(() => {
      void result.current.connect();
    });

    const firstSocket = MockWebSocket.instances[0];
    act(() => {
      firstSocket.open();
      firstSocket.emit({ type: 'auth.ok', session_id: 'session-1' });
    });

    await waitFor(() => {
      expect(result.current.connectionState).toBe('connected');
    });

    act(() => {
      firstSocket.close();
      jest.advanceTimersByTime(1500);
    });

    const secondSocket = MockWebSocket.instances[1];
    expect(secondSocket).toBeDefined();

    act(() => {
      secondSocket.open();
      secondSocket.emit({ type: 'auth.ok', session_id: 'session-1' });
    });

    await waitFor(() => {
      expect(result.current.connectionState).toBe('connected');
    });
  });
});
