import { useState, KeyboardEvent, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ImagePlus, Mic, Send, Square, X } from 'lucide-react';

interface MessageInputProps {
  onSend: (payload: { content: string; imageFile?: File | null; audioFile?: File | null }) => void;
  disabled: boolean;
}

export function MessageInput({ onSend, disabled }: MessageInputProps) {
  const [input, setInput] = useState('');
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordError, setRecordError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const handleSend = () => {
    if ((input.trim() || imageFile || audioFile) && !disabled) {
      onSend({ content: input.trim(), imageFile, audioFile });
      setInput('');
      setImageFile(null);
      setAudioFile(null);
      setRecordError(null);
    }
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const startRecording = async () => {
    try {
      setRecordError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        if (blob.size > 0) {
          const extension = blob.type.includes('ogg') ? 'ogg' : blob.type.includes('mp4') ? 'mp4' : 'webm';
          const file = new File([blob], `voice-query-${Date.now()}.${extension}`, { type: blob.type });
          setAudioFile(file);
        }
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      };

      mediaRecorderRef.current = recorder;
      recorder.start(250);
      setIsRecording(true);
    } catch {
      setRecordError('Microphone access was blocked. Please allow mic permission and retry.');
    }
  };

  const stopRecording = () => {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop();
    }
    setIsRecording(false);
  };

  useEffect(() => {
    return () => {
      const recorder = mediaRecorderRef.current;
      if (recorder && recorder.state !== 'inactive') {
        recorder.stop();
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  return (
    <div className="border-t p-4 bg-white">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <label className="inline-flex items-center">
          <input
            type="file"
            accept="image/*"
            className="hidden"
            disabled={disabled}
            onChange={(e) => setImageFile(e.target.files?.[0] ?? null)}
          />
          <span className="inline-flex cursor-pointer items-center rounded-md border px-2 py-1 text-xs text-gray-700 hover:bg-gray-50">
            <ImagePlus className="mr-1 h-3.5 w-3.5" />
            Add Image
          </span>
        </label>
        {!isRecording ? (
          <button
            type="button"
            onClick={startRecording}
            disabled={disabled}
            className="inline-flex items-center rounded-md border px-2 py-1 text-xs text-gray-700 hover:bg-gray-50"
          >
            <Mic className="mr-1 h-3.5 w-3.5" />
            Speak
          </button>
        ) : (
          <button
            type="button"
            onClick={stopRecording}
            disabled={disabled}
            className="inline-flex items-center rounded-md border border-red-300 bg-red-50 px-2 py-1 text-xs text-red-700 hover:bg-red-100"
          >
            <Square className="mr-1 h-3.5 w-3.5" />
            Stop
          </button>
        )}
      </div>

      {(imageFile || audioFile) && (
        <div className="mb-2 flex flex-wrap gap-2">
          {imageFile && (
            <div className="inline-flex items-center gap-1 rounded-full border bg-gray-50 px-2 py-1 text-xs text-gray-700">
              <span>{imageFile.name}</span>
              <button type="button" onClick={() => setImageFile(null)} disabled={disabled} aria-label="Remove image">
                <X className="h-3 w-3" />
              </button>
            </div>
          )}
          {audioFile && (
            <div className="inline-flex items-center gap-1 rounded-full border bg-gray-50 px-2 py-1 text-xs text-gray-700">
              <span>{audioFile.name}</span>
              <button type="button" onClick={() => setAudioFile(null)} disabled={disabled} aria-label="Remove audio">
                <X className="h-3 w-3" />
              </button>
            </div>
          )}
        </div>
      )}
      {recordError && <p className="mb-2 text-xs text-red-600">{recordError}</p>}

      <div className="flex gap-2">
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Describe your symptoms..."
          className="resize-none"
          rows={3}
          disabled={disabled}
        />
        <Button
          onClick={handleSend}
          disabled={disabled || (!input.trim() && !imageFile && !audioFile)}
          size="icon"
          className="self-end"
        >
          <Send className="w-4 h-4" />
        </Button>
      </div>
      <p className="text-xs text-gray-500 mt-2">
        Press Enter to send, Shift+Enter for new line. Use Speak to record voice directly, plus optional image.
      </p>
    </div>
  );
}
