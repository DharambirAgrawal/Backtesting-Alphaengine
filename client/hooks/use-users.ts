"use client";

import useSWR from "swr";
import { getUsers } from "@/lib/api";
import type { User } from "@/lib/types";

export function useUsers() {
  const { data, error, isLoading, mutate } = useSWR<User[]>(
    "users",
    getUsers,
    {
      revalidateOnFocus: false,
    }
  );

  return {
    users: data ?? [],
    isLoading,
    error,
    refresh: mutate,
  };
}
