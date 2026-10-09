import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Message } from '../types/chat';

interface ChatState {
  messages: Message[];
  sessionId: string | null;
  isLoading: boolean;
  
  addMessage: (message: Message) => void;
  setMessages: (messages: Message[]) => void;
  setSessionId: (id: string) => void;
  setLoading: (loading: boolean) => void;
  clearChat: () => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      messages: [],
      sessionId: null,
      isLoading: false,
      
      addMessage: (message) =>
        set((state) => ({ messages: [...state.messages, message] })),
      
      setMessages: (messages) => set({ messages }),
      
      setSessionId: (id) => set({ sessionId: id }),
      
      setLoading: (loading) => set({ isLoading: loading }),
      
      clearChat: () => set({ messages: [], sessionId: null }),
    }),
    {
      name: 'chat-storage', // unique name
      partialize: (state) => ({ sessionId: state.sessionId, messages: state.messages }), // Only persist these
      merge: (persistedState, currentState) => {
        const typed = (persistedState as Partial<ChatState>) || {};
        const normalizedMessages = (typed.messages || []).map((message) => ({
          ...message,
          // Persist serializes Date to string; restore Date on hydration.
          timestamp: new Date(message.timestamp as unknown as string),
        }));

        return {
          ...currentState,
          ...typed,
          messages: normalizedMessages,
        };
      },
    }
  )
);