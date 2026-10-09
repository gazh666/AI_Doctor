const nextJest = require('next/jest')

/**
 * Providing the path to your Next.js app will load next.config.js 
 * and .env files in your test environment.
 */
const createJestConfig = nextJest({
  dir: './',
})

/** @type {import('jest').Config} */
const customJestConfig = {
  // Points to your polyfills and global test mocks
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],

  testEnvironment: 'jest-environment-jsdom',

  moduleNameMapper: {
  '^@/(.*)$': '<rootDir>/src/$1',
  // Direct mapping for Radix primitives
  '^@radix-ui/react-(.*)$': '<rootDir>/node_modules/@radix-ui/react-$1',
  // Fallback for generic radix-ui imports if any other components use them
  '^radix-ui$': '<rootDir>/node_modules/@radix-ui/react-scroll-area', 
},

  transformIgnorePatterns: [
    '/node_modules/(?!(ai|@ai-sdk|@radix-ui|lucide-react|nanoid|clsx|tailwind-merge)/)',
  ],

  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.stories.{js,jsx,ts,tsx}',
    '!src/**/_*.{js,jsx,ts,tsx}',
    '!src/types/**/*',
    '!src/components/ui/**', // Often excluded as these are shadcn primitives
  ],

  testMatch: [
    '**/__tests__/**/*.[jt]s?(x)',
    '**/?(*.)+(spec|test).[jt]s?(x)',
  ],

  testPathIgnorePatterns: [
    '<rootDir>/node_modules/',
    '<rootDir>/.next/'
  ],

  // Ensures clear output for each individual clinical test
  verbose: true,
}

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
module.exports = createJestConfig(customJestConfig)