'use client';

import { useMemo } from 'react';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useChat } from '@/hooks/useChat';
import { useChatStore } from '@/store/chatStore';
import { AlertTriangle, RefreshCw } from 'lucide-react';

import { MessageInput } from './MessageInput';
import { MessageList } from './MessageList';

export function ChatInterface() {
  const { messages, isLoading, error, sendMessage } = useChat();
  const clearChat = useChatStore((state) => state.clearChat);

  const latestCriticalMessage = useMemo(() => {
    return [...messages]
      .reverse()
      .find((msg) => msg.role === 'assistant' && msg.metadata?.status === 'CRITICAL');
  }, [messages]);

  const latestCriticalMetadata: any = useMemo(() => {
    const meta = (latestCriticalMessage?.metadata ?? {}) as any;
    if (meta?.emergency_info && typeof meta.emergency_info === 'object') {
      return {
        ...meta.emergency_info,
        ...meta,
        status: meta.status ?? meta.emergency_info.status,
      };
    }
    return meta;
  }, [latestCriticalMessage]);

  const fallbackFacility = useMemo(() => {
    const content = latestCriticalMessage?.content ?? '';
    const match = content.match(/Nearest CHC:\s*(.+?)\s*\(([\d.]+)\s*km\)\s*\|\s*([+\d\- ]+)/i);
    if (!match) return null;

    return {
      name: match[1].trim(),
      distance_km: Number(match[2]),
      contact_number: match[3].trim(),
      coordinates: latestCriticalMetadata?.user_location,
    };
  }, [latestCriticalMessage, latestCriticalMetadata?.user_location]);

  const nearestFacility = latestCriticalMetadata?.nearby_facilities?.[0] ?? fallbackFacility;
  const isCritical = latestCriticalMetadata?.status === 'CRITICAL';
  return (
    <div className="h-screen flex flex-col">
      <div className={`border-b p-4 flex items-center justify-between ${isCritical ? 'bg-red-50 border-red-300' : 'bg-white'}`}>
        <div>
          <p className={`text-sm ${isCritical ? 'text-red-700 font-semibold' : 'text-gray-600'}`}>
            {isCritical ? 'Emergency Mode Active - Immediate Action Required' : 'Your AI Medical Assistant'}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={clearChat} disabled={messages.length === 0}>
          <RefreshCw className="w-4 h-4 mr-2" />
          New Chat
        </Button>
      </div>

      <Card className={`flex-1 flex flex-col m-4 overflow-hidden ${isCritical ? 'border-red-500 border-2' : ''}`}>
        {isCritical && latestCriticalMetadata && (
          <div className="border-b border-red-300 bg-red-50 p-4 space-y-3">
            <div className="flex items-start gap-2 text-red-900">
              <AlertTriangle className="w-5 h-5 mt-0.5" />
              <div>
                <p className="font-semibold">CRITICAL: Potential life-threatening symptoms detected.</p>
                {latestCriticalMetadata.red_flags && latestCriticalMetadata.red_flags.length > 0 && (
                  <p className="text-sm">Red flags: {latestCriticalMetadata.red_flags.join(', ')}</p>
                )}
              </div>
            </div>

            {nearestFacility && (
              <div className="rounded-md border border-red-200 bg-white p-3">
                {nearestFacility?.name && (
                  <p className="font-medium text-sm text-red-900">Nearest Facility: {nearestFacility.name}</p>
                )}
                {nearestFacility?.distance_km != null && nearestFacility?.contact_number && (
                  <p className="text-sm text-gray-700">
                    Distance: {nearestFacility.distance_km} km | Contact: {nearestFacility.contact_number}
                  </p>
                )}
              </div>
            )}

            {latestCriticalMetadata.first_aid_instructions && latestCriticalMetadata.first_aid_instructions.length > 0 && (
              <div className="rounded-md border border-red-200 bg-white p-3">
                <p className="text-sm font-semibold text-red-900">First Aid Instructions</p>
                <ul className="text-sm text-gray-800 mt-1 list-disc list-inside">
                  {latestCriticalMetadata.first_aid_instructions.map((item: string, idx: number) => (
                    <li key={`${item}-${idx}`}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        <MessageList messages={messages} isLoading={isLoading} />

        {error && (
          <div className="px-4 py-2 bg-red-50 border-t border-red-200">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        <MessageInput onSend={sendMessage} disabled={isLoading} />
      </Card>
    </div>
  );
}
