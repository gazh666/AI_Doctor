'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/auth/authContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card } from '@/components/ui/card';
import { Loader2 } from 'lucide-react';
import { useRouter } from 'next/navigation';

export function RegisterForm() {
  const router = useRouter();
  const { register } = useAuth();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    full_name: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const getErrorMessage = (err: unknown): string => {
    if (typeof err === 'string') {
      return err;
    }

    if (err && typeof err === 'object') {
      const maybeAxiosError = err as {
        response?: {
          data?: {
            detail?: string | string[];
            error?: { message?: string };
          };
        };
        message?: string;
      };
      const detail = maybeAxiosError.response?.data?.detail;
      const wrappedMessage = maybeAxiosError.response?.data?.error?.message;

      if (typeof detail === 'string' && detail.trim().length > 0) {
        return detail;
      }

      if (Array.isArray(detail) && detail.length > 0) {
        return detail.join(', ');
      }

      if (typeof wrappedMessage === 'string' && wrappedMessage.trim().length > 0) {
        return wrappedMessage;
      }

      if (typeof maybeAxiosError.message === 'string' && maybeAxiosError.message.trim().length > 0) {
        return maybeAxiosError.message;
      }
    }

    return 'Registration failed';
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Validation
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setLoading(true);

    try {
      await register({
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name,
      });
      router.push('/dashboard');
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-md p-8">
      <h2 className="text-2xl font-bold mb-6 text-center">Create Account</h2>

      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-300 text-red-800 rounded">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <Label htmlFor="full_name">Full Name</Label>
          <Input
            id="full_name"
            value={formData.full_name}
            onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
            disabled={loading}
          />
        </div>

        <div>
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            required
            disabled={loading}
          />
        </div>

        <div>
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            required
            disabled={loading}
            minLength={8}
          />
          <p className="text-xs text-gray-500 mt-1">Minimum 8 characters</p>
        </div>

        <div>
          <Label htmlFor="confirmPassword">Confirm Password</Label>
          <Input
            id="confirmPassword"
            type="password"
            value={formData.confirmPassword}
            onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
            required
            disabled={loading}
          />
        </div>

        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Creating account...
            </>
          ) : (
            'Register'
          )}
        </Button>
      </form>

      <div className="mt-4 text-center">
        <span className="text-sm text-gray-600">Already have an account? </span>
        <a href="/login" className="text-sm text-blue-600 hover:underline">
          Login
        </a>
      </div>
    </Card>
  );
}