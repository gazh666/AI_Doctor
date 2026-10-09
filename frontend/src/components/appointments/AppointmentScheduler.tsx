'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import apiClient from '@/lib/api/client';
import { format } from 'date-fns';

export function AppointmentScheduler() {
  const [date, setDate] = useState<Date | undefined>(new Date());
  const [dateInput, setDateInput] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [availableSlots, setAvailableSlots] = useState<string[]>([]);
  const [selectedSlot, setSelectedSlot] = useState('');
  const [appointmentType, setAppointmentType] = useState('consultation');
  const [notes, setNotes] = useState('');
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [slotsError, setSlotsError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (date) {
      loadAvailableSlots();
    }
  }, [date]);

  const loadAvailableSlots = async () => {
    if (!date) return;

    setSlotsLoading(true);
    setSlotsError(null);
    setSelectedSlot('');

    try {
      const response = await apiClient.get('/appointments/slots/available', {
        params: { date: format(date, 'yyyy-MM-dd') },
      });

      const slots = response.data.map((slot: string) =>
        format(new Date(slot), 'HH:mm')
      );
      setAvailableSlots(slots);
    } catch (error: any) {
      setAvailableSlots([]);
      const detail = error?.response?.data?.detail;
      const fallback = 'Unable to load available slots. Please try again or check backend connectivity.';
      setSlotsError(typeof detail === 'string' ? detail : fallback);
      console.error('Failed to load slots:', error);
    } finally {
      setSlotsLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!date || !selectedSlot) {
      alert('Please select a date and time');
      return;
    }

    setLoading(true);

    try {
      const [hours, minutes] = selectedSlot.split(':');
      const scheduledDate = new Date(date);
      scheduledDate.setHours(parseInt(hours), parseInt(minutes));

      await apiClient.post('/appointments/', {
        appointment_type: appointmentType,
        scheduled_date: scheduledDate.toISOString(),
        duration_minutes: 30,
        notes,
      });

      alert('Appointment scheduled successfully!');
      setNotes('');
      loadAvailableSlots();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to schedule appointment');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">Schedule Appointment</h3>

      <div className="space-y-4">
        <div>
          <Label>Select Date</Label>
          <Input
            type="date"
            value={dateInput}
            min={format(new Date(), 'yyyy-MM-dd')}
            onChange={(e) => {
              const value = e.target.value;
              setDateInput(value);
              if (value) {
                setDate(new Date(`${value}T00:00:00`));
              }
            }}
          />
        </div>

        <div>
          <Label>Appointment Type</Label>
          <Select value={appointmentType} onValueChange={setAppointmentType}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="consultation">Consultation</SelectItem>
              <SelectItem value="followup">Follow-up</SelectItem>
              <SelectItem value="emergency">Emergency</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label>Available Time Slots</Label>
          <Select value={selectedSlot} onValueChange={setSelectedSlot}>
            <SelectTrigger>
              <SelectValue placeholder="Select time" />
            </SelectTrigger>
            <SelectContent>
              {slotsLoading ? (
                <SelectItem value="loading" disabled>
                  Loading slots...
                </SelectItem>
              ) : availableSlots.length === 0 ? (
                <SelectItem value="none" disabled>
                  No slots available
                </SelectItem>
              ) : (
                availableSlots.map((slot) => (
                  <SelectItem key={slot} value={slot}>
                    {slot}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
          {slotsError ? (
            <p className="mt-2 text-sm text-red-600">
              Backend error: {slotsError}
            </p>
          ) : null}
          {!slotsLoading && !slotsError && availableSlots.length === 0 ? (
            <p className="mt-2 text-sm text-amber-700">
              No slots available for this date. Try another date.
            </p>
          ) : null}
        </div>

        <div>
          <Label>Notes (optional)</Label>
          <Textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Any specific concerns or symptoms..."
            rows={3}
          />
        </div>

        <Button onClick={handleSubmit} disabled={loading} className="w-full">
          {loading ? 'Scheduling...' : 'Schedule Appointment'}
        </Button>
      </div>
    </Card>
  );
}
