'use client';

import { useAuth } from '@/lib/auth/authContext';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu';
import { User, LogOut, Settings, History, CalendarClock, Download, FlaskConical, BookOpen } from 'lucide-react';
import Link from 'next/link';

export function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();

  return (
    <nav className="border-b">
      <div className="container mx-auto px-4 py-3 flex justify-between items-center">
        <Link href="/" className="text-xl font-bold">
          Rural AI Doctor
        </Link>

        <div className="flex items-center gap-4">
          {isAuthenticated ? (
            <>
              <Link href="/dashboard">
                <Button variant="ghost">Dashboard</Button>
              </Link>

              <Link href="/diagnosis">
                <Button variant="ghost">New Diagnosis</Button>
              </Link>

              <Link href="/rag">
                <Button variant="ghost">RAG</Button>
              </Link>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon">
                    <User className="w-5 h-5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem asChild>
                    <Link href="/profile" className="flex items-center cursor-pointer">
                      <Settings className="w-4 h-4 mr-2" />
                      Profile Settings
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link href="/history" className="flex items-center cursor-pointer">
                      <History className="w-4 h-4 mr-2" />
                      History
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link href="/appointments" className="flex items-center cursor-pointer">
                      <CalendarClock className="w-4 h-4 mr-2" />
                      Appointments
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link href="/export" className="flex items-center cursor-pointer">
                      <Download className="w-4 h-4 mr-2" />
                      Export Data
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link href="/clinical-ops" className="flex items-center cursor-pointer">
                      <FlaskConical className="w-4 h-4 mr-2" />
                      Clinical Ops
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link href="/rag" className="flex items-center cursor-pointer">
                      <BookOpen className="w-4 h-4 mr-2" />
                      RAG Assistant
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={logout} className="cursor-pointer">
                    <LogOut className="w-4 h-4 mr-2" />
                    Logout
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>

              <span className="text-sm text-gray-600">{user?.email}</span>
            </>
          ) : (
            <>
              <Link href="/login">
                <Button variant="ghost">Login</Button>
              </Link>
              <Link href="/register">
                <Button>Get Started</Button>
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}