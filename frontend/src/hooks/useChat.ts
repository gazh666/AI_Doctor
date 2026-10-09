import { useState } from 'react';
import { useChatStore } from '../store/chatStore';
import { chatAPI } from '../lib/api/chat';
import { Message, MessageAttachment } from '../types/chat';

async function getCurrentLocation(): Promise<{ lat: number; lng: number } | undefined> {
  if (typeof window === 'undefined' || !navigator.geolocation) {
    return undefined;
  }

  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        });
      },
      () => resolve(undefined),
      // Slightly longer timeout and non-high-accuracy mode improve success rate on desktop browsers.
      { enableHighAccuracy: false, timeout: 12000, maximumAge: 120000 },
    );
  });
}

export function useChat() {
  const { messages, sessionId, isLoading, addMessage, setSessionId, setLoading } = useChatStore();
  const [error, setError] = useState<string | null>(null);

  const sendMessage = async (
    payload: string | { content: string; imageFile?: File | null; audioFile?: File | null }
  ) => {
    try {
      setError(null);
      setLoading(true);

      const content = typeof payload === 'string' ? payload : payload.content;
      const imageFile = typeof payload === 'string' ? null : payload.imageFile ?? null;
      const audioFile = typeof payload === 'string' ? null : payload.audioFile ?? null;
      const hasAttachments = Boolean(imageFile || audioFile);

      if (!content.trim() && !hasAttachments) {
        setLoading(false);
        return;
      }

      const attachments: MessageAttachment[] = [];
      if (imageFile) {
        attachments.push({ type: 'image', name: imageFile.name });
      }
      if (audioFile) {
        attachments.push({ type: 'audio', name: audioFile.name });
      }

      const userContent = content.trim();
      const visibleUserText = userContent || attachments.map((a) => `[${a.type}] ${a.name}`).join('\n');
      const outgoingContent = userContent;

      
      const userMessage: Message = {
        id: Date.now().toString(),
        role: 'user',
        content: visibleUserText,
        timestamp: new Date(),
        attachments: attachments.length ? attachments : undefined,
      };
      addMessage(userMessage);

      
      const userLocation = await getCurrentLocation();
      const messageHistory = [
        ...messages.map(m => ({ role: m.role, content: m.content })),
        { role: 'user' as const, content: outgoingContent },
      ];
      const request = {
        messages: messageHistory,
        session_id: sessionId || undefined,
        user_location: userLocation,
      };

      let response;
      if (hasAttachments) {
        const formData = new FormData();
        formData.append('messages', JSON.stringify(messageHistory));
        if (sessionId) {
          formData.append('session_id', sessionId);
        }
        if (userLocation) {
          formData.append('user_location', JSON.stringify(userLocation));
        }
        if (imageFile) {
          formData.append('image', imageFile);
        }
        if (audioFile) {
          formData.append('audio', audioFile);
        }

        response = await chatAPI.sendMessage(formData);
      } else {
        response = await chatAPI.sendMessage(request);
      }

      
      if (!sessionId) {
        setSessionId(response.session_id);
      }

      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.message,
        timestamp: new Date(response.timestamp),
        metadata: response.metadata,
      };
      addMessage(assistantMessage);

    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send message');
      console.error('Chat error:', err);
    } finally {
      setLoading(false);
    }
  };

  return {
    messages,
    isLoading,
    error,
    sendMessage,
  };
}
