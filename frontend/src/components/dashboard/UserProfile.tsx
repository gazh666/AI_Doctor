'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth/authContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card } from '@/components/ui/card';
import { authAPI } from '@/lib/api/auth';
import { Loader2 } from 'lucide-react';

export function UserProfile() {
  const { user } = useAuth();
  const [formData, setFormData] = useState({
    full_name: '',
    phone: '',
    gender: '',
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (user) {
      setFormData({
        full_name: user.full_name || '',
        phone: '',
        gender: '',
      });
    }
  }, [user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      await authAPI.updateProfile(formData);
      setMessage('Profile updated successfully!');
    } catch (error) {
      setMessage('Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="p-6 max-w-2xl">
      <h2 className="text-2xl font-bold mb-6">Profile Settings</h2>

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
          <Label htmlFor="email">Email</Label>
          <Input id="email" value={user?.email || ''} disabled />
        </div>

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
          <Label htmlFor="phone">Phone</Label>
          <Input
            id="phone"
            value={formData.phone}
            onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
            disabled={loading}
          />
        </div>

        <div>
          <Label htmlFor="gender">Gender</Label>
          <Input
            id="gender"
            value={formData.gender}
            onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
            disabled={loading}
          />
        </div>

        <Button type="submit" disabled={loading}>
          {loading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Updating...
            </>
          ) : (
            'Update Profile'
          )}
        </Button>
      </form>
    </Card>
  );
}