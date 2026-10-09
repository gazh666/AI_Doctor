import { Message } from '@/types/chat';
import { Button } from '@/components/ui/button';
import { cn } from 'lib/utils';
import { User, Bot, ExternalLink, PhoneCall } from 'lucide-react';

interface ChatBubbleProps {
  message: Message;
}

export function ChatBubble({ message }: ChatBubbleProps) {
  const isUser = message.role === 'user';
  const isCriticalAssistant = !isUser && message.metadata?.status === 'CRITICAL';
  const mapsUrl = 'https://www.google.com/maps/search/?api=1&query=hospital+near+me';
  const parsedTimestamp = message.timestamp instanceof Date
    ? message.timestamp
    : new Date(message.timestamp as unknown as string);
  const timeLabel = Number.isNaN(parsedTimestamp.getTime())
    ? 'Unknown time'
    : parsedTimestamp.toLocaleTimeString();

  return (
    <div className={cn(
      'flex gap-3 mb-4',
      isUser ? 'flex-row-reverse' : 'flex-row'
    )}>
      <div className={cn(
        'shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
        isUser ? 'bg-blue-500' : 'bg-green-500'
      )}>
        {isUser ? (
          <User className="w-5 h-5 text-white" />
        ) : (
          <Bot className="w-5 h-5 text-white" />
        )}
      </div>

      <div className={cn(
        'flex flex-col max-w-[70%]',
        isUser ? 'items-end' : 'items-start'
      )}>
        <div className={cn(
          'rounded-lg px-4 py-2 wrap-break-words',
          isUser
            ? 'bg-blue-500 text-white'
            : isCriticalAssistant
              ? 'bg-red-100 text-red-950 border border-red-300'
              : 'bg-gray-100 text-gray-900'
        )}>
          {isCriticalAssistant && (
            <p className="text-xs font-bold uppercase mb-1">Critical Alert</p>
          )}
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          {isUser && message.attachments && message.attachments.length > 0 && (
            <div className="mt-2 space-y-1">
              {message.attachments.map((attachment, index) => (
                <p key={`${attachment.type}-${attachment.name}-${index}`} className="text-xs text-blue-100">
                  {attachment.type.toUpperCase()}: {attachment.name}
                </p>
              ))}
            </div>
          )}
          {isCriticalAssistant && mapsUrl && (
            <div className="mt-3 flex gap-2 flex-wrap">
              <Button asChild size="sm" className="bg-red-600 hover:bg-red-700">
                <a href="tel:108">
                  <PhoneCall className="w-4 h-4 mr-2" />
                  Call 108
                </a>
              </Button>
              <Button asChild size="sm" className="bg-red-700 hover:bg-red-800">
                <a href="tel:102">
                  <PhoneCall className="w-4 h-4 mr-2" />
                  Call 102
                </a>
              </Button>
              {mapsUrl && (
                <Button asChild size="sm" variant="outline">
                  <a href={mapsUrl} target="_blank" rel="noreferrer">
                    <ExternalLink className="w-4 h-4 mr-2" />
                    Nearby Hospitals
                  </a>
                </Button>
              )}
            </div>
          )}
        </div>
        <span className="text-xs text-gray-500 mt-1">
          {timeLabel}
        </span>
      </div>
    </div>
  );
}
