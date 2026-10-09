import { useEffect, useRef } from 'react';
import { ChatBubble } from './ChatBubble';
import { Message } from '@/types/chat';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Bot,Loader2 } from 'lucide-react';


interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
}

export function MessageList({ messages, isLoading }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <ScrollArea className="flex-1 p-4 h-full [&>div>div]:flex [&>div>div]:flex-col [&>div>div]:justify-end">
      {messages.length === 0 ? (
        <div className="flex items-center justify-center h-full text-gray-500">
          <div className="text-center">
            <Bot className="w-12 h-12 mx-auto mb-4 text-gray-400" />
            <p>Start a conversation with Dr. AI</p>
            <p className="text-sm mt-2">Describe your symptoms or ask a health question</p>
          </div>
        </div>
      ) : (
        <>
          {messages.map((message) => (
            <ChatBubble key={message.id} message={message} />
          ))}
          {isLoading && (
            <div className="flex items-center gap-2 text-gray-500 mb-4">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm">Dr. AI is thinking...</span>
            </div>
          )}
          <div ref={bottomRef} />
        </>
      )}
    </ScrollArea>
  );
}