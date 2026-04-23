"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  ArrowRightLeft,
  Brain,
  Settings,
  Users,
  Layers3,
  ChevronLeft,
  TrendingUp,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { useEffect, useState } from "react";

interface SidebarProps {
  portfolioId?: string;
}

export function Sidebar({ portfolioId }: SidebarProps) {
  const pathname = usePathname();
  const { role, logout, isReady } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const isLinkActive = (href: string, exact = false) => {
    if (exact) {
      return pathname === href;
    }

    return pathname === href || pathname.startsWith(`${href}/`);
  };

  const mainNavItems = [
    {
      label: portfolioId ? "Overview" : "Portfolios",
      href: portfolioId ? `/dashboard/${portfolioId}` : "/dashboard",
      icon: LayoutDashboard,
      exact: !portfolioId,
    },
    {
      label: "Model Registry",
      href: "/dashboard/models",
      icon: Layers3,
      exact: false,
    },
    ...(portfolioId
      ? [
          {
            label: "Trades",
            href: `/dashboard/${portfolioId}/trades`,
            icon: ArrowRightLeft,
            exact: false,
          },
          {
            label: "Portfolio Models",
            href: `/dashboard/${portfolioId}/models`,
            icon: Brain,
            exact: false,
          },
          {
            label: "Settings",
            href: `/portfolios/${portfolioId}/settings`,
            icon: Settings,
            exact: false,
          },
        ]
      : []),
  ];

  const adminNavItems =
    mounted && isReady && role === "admin"
      ? [
          {
            label: "Users",
            href: "/admin/users",
            icon: Users,
          },
        ]
      : [];

  return (
    <aside
      className={cn(
        "flex h-screen flex-col border-r border-sidebar-border bg-sidebar transition-all duration-300",
        collapsed ? "w-16" : "w-64"
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center justify-between border-b border-sidebar-border px-4">
        {!collapsed && (
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10">
              <TrendingUp className="h-4 w-4 text-primary" />
            </div>
            <span className="font-semibold text-sidebar-foreground">
              AlphaEngine
            </span>
          </Link>
        )}
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => setCollapsed(!collapsed)}
          className="text-sidebar-foreground hover:bg-sidebar-accent"
        >
          <ChevronLeft
            className={cn(
              "h-4 w-4 transition-transform",
              collapsed && "rotate-180"
            )}
          />
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-2">
        {mainNavItems.map((item) => {
          const isActive = isLinkActive(item.href, item.exact);
          return (
            <Link
              key={item.href}
              href={item.href}
              prefetch
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-accent text-sidebar-primary"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground"
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}

        {adminNavItems.length > 0 && (
          <>
            {!collapsed && (
              <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-sidebar-foreground/50">
                Admin
              </div>
            )}
            {adminNavItems.map((item) => {
              const isActive = isLinkActive(item.href, true);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  prefetch
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-sidebar-accent text-sidebar-primary"
                      : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground"
                  )}
                >
                  <item.icon className="h-4 w-4 shrink-0" />
                  {!collapsed && <span>{item.label}</span>}
                </Link>
              );
            })}
          </>
        )}
      </nav>

      {/* Logout */}
      <div className="border-t border-sidebar-border p-2">
        <Button
          variant="ghost"
          onClick={logout}
          className={cn(
            "w-full justify-start gap-3 text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground",
            collapsed && "justify-center"
          )}
        >
          <LogOut className="h-4 w-4 shrink-0" />
          {!collapsed && <span>Sign Out</span>}
        </Button>
      </div>
    </aside>
  );
}
