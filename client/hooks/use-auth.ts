"use client";

import { useRouter } from "next/navigation";
import { useState, useCallback } from "react";
import { login as loginApi, getMe } from "@/lib/api";
import {
  saveToken,
  getToken,
  getRole,
  getEmail,
  isAuthenticated,
  logout as authLogout,
} from "@/lib/auth";
import type { User } from "@/lib/types";
import useSWR from "swr";

export function useAuth() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch current user data if authenticated
  const {
    data: user,
    isLoading: isUserLoading,
    mutate: mutateUser,
  } = useSWR<User>(isAuthenticated() ? "user" : null, getMe, {
    revalidateOnFocus: false,
    onError: () => {
      // If fetching user fails, logout
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
        await mutateUser();
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
    [router, mutateUser]
  );

  const logout = useCallback(() => {
    authLogout();
  }, []);

  return {
    user,
    login,
    logout,
    isLoading: isLoading || isUserLoading,
    error,
    isAuthenticated: isAuthenticated(),
    role: getRole(),
    email: getEmail(),
    token: getToken(),
  };
}
