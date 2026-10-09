export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  attachments?: MessageAttachment[];
  metadata?: MessageMetadata;
}

export interface MessageAttachment {
  type: 'image' | 'audio';
  name: string;
}

export interface ChatSession {
  id: string;
  messages: Message[];
  createdAt: Date;
}

export type SeverityLevel = 'EMERGENCY' | 'URGENT' | 'ROUTINE' | 'SELF-CARE';

export interface SymptomAnalysis {
  analysis: string;
  severity: SeverityLevel;
  possibleConditions: string[];
  recommendations: string;
}

export interface EmergencyFacility {
  name: string;
  distance_km: number;
  contact_number: string;
  coordinates: {
    lat: number;
    lng: number;
  };
}

export interface MessageMetadata {
  status?: 'CRITICAL' | 'OK';
  red_flags?: string[];
  user_location?: {
    lat: number;
    lng: number;
  };
  nearby_facilities?: EmergencyFacility[];
  first_aid_instructions?: string[];
  input_modalities?: {
    image?: {
      filename?: string;
      image_type?: string;
      severity?: string;
      confidence?: number;
    };
    audio?: {
      filename?: string;
      transcription?: string;
    };
  };
}
