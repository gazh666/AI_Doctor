// src/declarations.d.ts
declare module '@testing-library/react' {
  import { ReactElement } from 'react';
  
  export function render(ui: ReactElement, options?: any): any;
  export const screen: any;
  export const fireEvent: any;
  export function waitFor(callback: () => any, options?: any): Promise<any>;
  export function cleanup(): void;
  // Add any other members you're using, like 'within' or 'configure'
}