import { Loader2 } from 'lucide-react';

export function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center p-4">
      <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
    </div>
  );
}