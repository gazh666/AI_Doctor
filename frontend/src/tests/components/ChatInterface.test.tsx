import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { useChat } from '@ai-sdk/react'; 

jest.mock('@ai-sdk/react', () => ({
  useChat: jest.fn(),
}));

describe('ChatInterface Clinical Flow', () => {
  const mockUseChat = useChat as jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseChat.mockReturnValue({
      messages: [],
      input: '',
      handleInputChange: jest.fn(),
      handleSubmit: (e: React.FormEvent) => e.preventDefault(),
      isLoading: false,
    });
  });

  it('renders and finds the clinical input', () => {
    render(<ChatInterface />);
    
    // FIX: Updated to match your actual placeholder: "Describe your symptoms..."
    const input = screen.getByPlaceholderText(/describe your symptoms/i);
    expect(input).toBeInTheDocument();
    
    // Check for the "New Chat" button to ensure header rendered
    expect(screen.getByText(/new chat/i)).toBeInTheDocument();
  });
});