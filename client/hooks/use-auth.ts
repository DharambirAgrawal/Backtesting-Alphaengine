"use client";

import { useRouter } from "next/navigation";
import { useState, useCallback, useEffect } from "react";
import { login as loginApi, getMe } from "@/lib/api";
import {
  saveToken,
  getToken,
  getRole,
  getEmail,
  logout as authLogout,
} from "@/lib/auth";
import type { User, UserRole } from "@/lib/types";
import useSWR from "swr";

interface AuthSessionState {
  token: string | null;
  role: UserRole | null;
  email: string | null;
  isReady: boolean;
}

export function useAuth() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<AuthSessionState>({
    token: null,
    role: null,
    email: null,
    isReady: false,
  });

  useEffect(() => {
    setSession({
      token: getToken(),
      role: getRole() as UserRole | null,
      email: getEmail(),
      isReady: true,
    });
  }, []);

  // Fetch current user data if authenticated
  const {
    data: user,
    isLoading: isUserLoading,
  } = useSWR<User>(session.isReady && session.token ? "user" : null, getMe, {
    revalidateOnFocus: false,
    onError: () => {
      // If fetching user fails, logout
      setSession({
        token: null,
        role: null,
        email: null,
        isReady: true,
      });
      authLogout();
    },
  });

  const login = useCallback(
    async (email: string, password: string) => {
      setIsLoading(true);
      setError(null);

      try {
        const data = await loginApi(email, password);
        saveToken(data.token, data.role, data.email);
        setSession({
          token: data.token,
          role: data.role,
          email: data.email,
          isReady: true,
        });
        router.push("/dashboard");
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Invalid email or password"
        );
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [router]
  );

  const logout = useCallback(() => {
    setSession({
      token: null,
      role: null,
      email: null,
      isReady: true,
    });
    authLogout();
  }, []);

  return {
    user,
    login,
    logout,
    isLoading: isLoading || (session.isReady ? isUserLoading : false),
    error,
    isReady: session.isReady,
    isAuthenticated: session.isReady ? Boolean(session.token) : false,
    role: user?.role ?? session.role,
    email: user?.email ?? session.email,
    token: session.token,
  };
}
