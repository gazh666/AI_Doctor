import '@testing-library/jest-dom';

/**
 * POLYFILL: TextEncoder, TextDecoder, & Web Streams
 * Required for the Vercel AI SDK to process medical diagnostic streams.
 */
if (typeof global.TextEncoder === 'undefined') {
  const { TextEncoder, TextDecoder } = require('util');
  global.TextEncoder = TextEncoder;
  global.TextDecoder = TextDecoder;
}

if (typeof global.ReadableStream === 'undefined') {
  // Using the native Node.js web streams
  const { 
    ReadableStream, 
    TransformStream, 
    WritableStream 
  } = require('node:stream/web');
  
  global.ReadableStream = ReadableStream;
  global.TransformStream = TransformStream;
  global.WritableStream = WritableStream;
}

/**
 * POLYFILL: Fetch API (Request, Response, Headers)
 * BETTER FIX: Instead of 'undici', we use the globals already provided 
 * by modern Node.js but often hidden by JSDOM.
 */
if (typeof global.fetch === 'undefined') {
  // We use the window (JSDOM) implementations which are safer for component testing
  global.fetch = window.fetch || jest.fn();
  global.Request = window.Request;
  global.Response = window.Response;
  global.Headers = window.Headers;
}

/**
 * UI MOCKS: IntersectionObserver & ResizeObserver
 * Essential for Shadcn components like ScrollArea used in the Chat Interface.
 */
class MockObserver {
  observe() { return null; }
  unobserve() { return null; }
  disconnect() { return null; }
}

Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  configurable: true,
  value: MockObserver,
});

Object.defineProperty(window, 'ResizeObserver', {
  writable: true,
  configurable: true,
  value: MockObserver,
});

/**
 * BROWSER UTILS: scrollTo
 * Prevents errors when the chat interface auto-scrolls to new medical advice.
 */
window.scrollTo = jest.fn();

/**
 * CONSOLE CLEANUP
 * Suppresses repetitive, harmless warnings from Tailwind and React 19.
 */
const originalConsoleError = console.error;
console.error = (...args) => {
  const errorMsg = typeof args[0] === 'string' ? args[0] : '';
  
  // Inside jest.setup.js console.error wrapper
// Inside jest.setup.js console.error wrapper
const suppressedErrors = [
  'Error: Could not parse CSS stylesheet',
  'Warning: React does not recognize the %s prop on a DOM element',
  'next-hydration-warning',
  'Chat error: Error: Network Error', // Hide expected test errors
  'act(...)', 
];

  if (suppressedErrors.some(msg => errorMsg.includes(msg))) {
    return;
  }
  
  originalConsoleError(...args);
};