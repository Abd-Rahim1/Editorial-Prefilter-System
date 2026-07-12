import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function proxy(request: NextRequest) {
  const path = request.nextUrl.pathname;

  // Read the user role stored in cookies during login
  const role = request.cookies.get('user_role')?.value;

  // 1. Protect Admin Routes
  if (path.startsWith('/admin')) {
    if (role !== 'admin') {
      // If not an admin, redirect back to login
      return NextResponse.redirect(new URL('/login', request.url));
    }
  }

  // 2. Protect Editor Routes
  if (path.startsWith('/editor')) {
    if (!role || (role !== 'editor' && role !== 'admin')) {
      // If not logged in as editor or admin, redirect to login
      return NextResponse.redirect(new URL('/login', request.url));
    }
  }

  // Allow the request to proceed if authorized
  return NextResponse.next();
}

// Specify exactly which routes this proxy should run on
export const config = {
  matcher: ['/admin/:path*', '/editor/:path*'],
};
