import { renderHook, act, cleanup } from '@testing-library/react';
import { useChat } from '@/hooks/useChat';
import { chatAPI } from '@/lib/api/chat';
import { useChatStore } from '@/store/chatStore';

// Mock the API specifically as an object to match hook usage
jest.mock('@/lib/api/chat', () => ({
  chatAPI: {
    sendMessage: jest.fn(),
  },
}));

describe('useChat Hook', () => {
  afterEach(() => {
    cleanup();
    jest.clearAllMocks();
    
    // Manual reset for the global Zustand store to ensure test isolation
    act(() => {
      useChatStore.setState({ 
        messages: [], 
        sessionId: null, 
        isLoading: false 
      });
    });
  });

  it('initializes with a clean clinical state', () => {
    const { result } = renderHook(() => useChat());
    expect(result.current.messages).toEqual([]);
    expect(result.current.isLoading).toBe(false);
  });

  it('updates the UI with user and assistant messages', async () => {
    const mockResponse = {
      message: "I understand. Do you have a fever?",
      session_id: "test-123",
      timestamp: new Date().toISOString()
    };

    (chatAPI.sendMessage as jest.Mock).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useChat());
    
    await act(async () => {
      await result.current.sendMessage('Severe headache');
    });

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[1].role).toBe('assistant');
  });

  it('handles API errors gracefully', async () => {
    (chatAPI.sendMessage as jest.Mock).mockRejectedValue(new Error("Network Error"));

    const { result } = renderHook(() => useChat());
    
    await act(async () => {
      await result.current.sendMessage('Help');
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.messages).toHaveLength(1);
  });
});