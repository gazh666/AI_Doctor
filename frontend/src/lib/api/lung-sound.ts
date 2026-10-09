import apiClient from './client';

export interface LungSoundResult {
  label: 'normal' | 'crackle' | 'wheeze' | 'both';
  confidence: number;
  probabilities?: Record<'normal' | 'crackle' | 'wheeze' | 'both', number> | null;
  audio_path: string;
  snr_db?: number | null;
  low_quality: boolean;
}

export interface LungSoundUploadResponse {
  lung_sound_path: string;
  result: LungSoundResult;
  message: string;
}

export const lungSoundAPI = {
  analyze: async (file: File): Promise<LungSoundUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<LungSoundUploadResponse>(
      '/lung_sound/analyze',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 90000,
      }
    );
    return response.data;
  },
};