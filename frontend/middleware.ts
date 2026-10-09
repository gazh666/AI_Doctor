import { NextRequest, NextResponse } from 'next/server';

const AUTH_COOKIE_NAME = 'rural_ai_auth';

const PROTECTED_PATHS = [
  '/dashboard',
  '/diagnosis',
  '/voice',
  '/xray',
  '/rag',
  '/history',
  '/appointments',
  '/export',
  '/profile',
  '/clinical-ops',
  '/admin',
  '/knowledge',
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isProtected = PROTECTED_PATHS.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`)
  );

  if (!isProtected) {
    return NextResponse.next();
  }

  const authCookie = request.cookies.get(AUTH_COOKIE_NAME)?.value;
  if (authCookie) {
    return NextResponse.next();
  }

  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = '/login';
  loginUrl.searchParams.set('next', pathname);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/diagnosis/:path*',
    '/voice/:path*',
    '/xray/:path*',
    '/rag/:path*',
    '/history/:path*',
    '/appointments/:path*',
    '/export/:path*',
    '/profile/:path*',
    '/clinical-ops/:path*',
    '/admin/:path*',
    '/knowledge/:path*',
  ],
};
