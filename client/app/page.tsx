"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/auth";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    // If user is logged in, go to dashboard; otherwise show landing page
    const token = getToken();
    if (token) {
      router.replace("/dashboard");
    } else {
      router.replace("/landing");
    }
  }, [router]);

  return null; // This page is just a redirect
}
