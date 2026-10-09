import {
  LiveVoiceConsultationClient,
  getVoiceLiveWebSocketUrl,
} from '@/lib/api/voice';

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

describe('LiveVoiceConsultationClient', () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    Object.defineProperty(global, 'WebSocket', {
      writable: true,
      value: MockWebSocket,
    });
  });

  it('builds websocket url from API base', () => {
    expect(getVoiceLiveWebSocketUrl()).toContain('/voice/live');
    expect(getVoiceLiveWebSocketUrl().startsWith('ws')).toBe(true);
  });

  it('sends auth frame after connection opens', async () => {
    const events: string[] = [];
    const client = new LiveVoiceConsultationClient();

    const connectPromise = client.connect('token-123', (event) => {
      events.push(event.type);
    });

    const socket = MockWebSocket.instances[0];
    socket.open();
    expect(socket.sent[0]).toContain('"type":"auth"');
    expect(socket.sent[0]).toContain('Bearer token-123');

    socket.emit({ type: 'auth.ok', session_id: 's-1' });
    await connectPromise;
    expect(events).toContain('auth.ok');
  });

  it('sends session configure and turn events', async () => {
    const client = new LiveVoiceConsultationClient();
    const connectPromise = client.connect('token-xyz', () => null);
    const socket = MockWebSocket.instances[0];

    socket.open();
    socket.emit({ type: 'auth.ok', session_id: 's-2' });
    await connectPromise;

    client.configureSession({ language: 'en', age: 30, gender: 'Male', medicalHistory: 'None' });
    client.startTurn('turn-1');
    client.endTurn('turn-1');
    client.ping();

    const sentText = socket.sent.join('\n');
    expect(sentText).toContain('"type":"session.configure"');
    expect(sentText).toContain('"type":"turn.start"');
    expect(sentText).toContain('"type":"turn.end"');
    expect(sentText).toContain('"type":"ping"');
  });
});
