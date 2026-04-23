import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_PATHS = ["/login"];

export function middleware(request: NextRequest) {
  const token = request.cookies.get("token")?.value;
  const path = request.nextUrl.pathname;

  // Allow public paths
  if (PUBLIC_PATHS.some((p) => path === p || path.startsWith(`${p}/`))) {
    // If logged in and visiting login, redirect to dashboard
    if (token && path === "/login") {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }
    return NextResponse.next();
  }

  // Allow API routes and static files
  if (
    path.startsWith("/api") ||
    path.startsWith("/_next") ||
    path.includes("favicon") ||
    path.includes(".")
  ) {
    return NextResponse.next();
  }

  // No token → redirect to login
  if (!token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Admin-only paths
  const role = request.cookies.get("role")?.value;
  if (path.startsWith("/admin") && role !== "admin") {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|icon|apple-icon).*)"],
};
