import apiClient from './client';

export interface ImageAnalysisResponse {
  analysis_id: number;
  image_type: string;
  findings: string;
  full_analysis: string;
  severity: string;
  confidence: number;
  recommendations: string;
  metadata: Record<string, any>;
  created_at: string;
}

export interface XRayAnalysisResponse {
  analysis_id: number;
  analysis: string;
  findings: string[];
  severity: string;
  confidence: number;
  differential_diagnosis: string[];
  recommendations: string;
  urgent_flags: string[];
}

export interface XRayAnalysisParams {
  file: File;
  symptoms?: string;
  age?: number;
  gender?: string;
  medicalHistory?: string;
}

export const visionAPI = {
  analyzeImage: async (
    file: File,
    imageType: string,
    patientContext?: string,
    enhanceImage: boolean = true,
    patientId?: number
  ): Promise<ImageAnalysisResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('image_type', imageType);
    if (patientContext) formData.append('patient_context', patientContext);
    formData.append('enhance_image', String(enhanceImage));
    if (patientId) formData.append('patient_id', String(patientId));

    const response = await apiClient.post('/vision/analyze', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },


  analyzeXRay: async (params: XRayAnalysisParams): Promise<XRayAnalysisResponse> => {
    const formData = new FormData();
    formData.append('file', params.file);
    if (params.symptoms) formData.append('symptoms', params.symptoms);
    if (params.age) formData.append('age', String(params.age));
    if (params.gender) formData.append('gender', params.gender);
    if (params.medicalHistory) formData.append('medical_history', params.medicalHistory);

    const response = await apiClient.post('/vision/xray/analyze', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout:90000
    });
    return response.data;
  },

  getAnalysis: async (analysisId: number): Promise<ImageAnalysisResponse> => {
    const response = await apiClient.get(`/vision/analysis/${analysisId}`);
    return response.data;
  },

  getHistory: async (limit: number = 10, imageType?: string) => {
    const params: any = { limit };
    if (imageType) params.image_type = imageType;

    const response = await apiClient.get('/vision/history', { params });
    return response.data;
  },
};