'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card } from '@/components/ui/card';
import { authAPI } from '@/lib/api/auth';
import { Loader2 } from 'lucide-react';

export function ChangePassword() {
  const [formData, setFormData] = useState({
    oldPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage('');

    if (formData.newPassword !== formData.confirmPassword) {
      setMessage('New passwords do not match');
      return;
    }

    if (formData.newPassword.length < 8) {
      setMessage('Password must be at least 8 characters');
      return;
    }

    setLoading(true);

    try {
      await authAPI.changePassword(formData.oldPassword, formData.newPassword);
      setMessage('Password changed successfully!');
      setFormData({ oldPassword: '', newPassword: '', confirmPassword: '' });
    } catch (error: any) {
      setMessage(error.response?.data?.detail || 'Failed to change password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="p-6 max-w-2xl">
      <h2 className="text-2xl font-bold mb-6">Change Password</h2>

      {message && (
        <div
          className={`mb-4 p-3 rounded ${
            message.includes('success')
              ? 'bg-green-100 text-green-800'
              : 'bg-red-100 text-red-800'
          }`}
        >
          {message}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <Label htmlFor="oldPassword">Current Password</Label>
          <Input
            id="oldPassword"
            type="password"
            value={formData.oldPassword}
            onChange={(e) => setFormData({ ...formData, oldPassword: e.target.value })}
            required
            disabled={loading}
          />
        </div>

        <div>
          <Label htmlFor="newPassword">New Password</Label>
          <Input
            id="newPassword"
            type="password"
            value={formData.newPassword}
            onChange={(e) => setFormData({ ...formData, newPassword: e.target.value })}
            required
            disabled={loading}
            minLength={8}
          />
        </div>

        <div>
          <Label htmlFor="confirmPassword">Confirm New Password</Label>
          <Input
            id="confirmPassword"
            type="password"
            value={formData.confirmPassword}
            onChange={(e) =>
              setFormData({ ...formData, confirmPassword: e.target.value })
            }
            required
            disabled={loading}
          />
        </div>

        <Button type="submit" disabled={loading}>
          {loading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Changing...
            </>
          ) : (
            'Change Password'
          )}
        </Button>
      </form>
    </Card>
  );
}