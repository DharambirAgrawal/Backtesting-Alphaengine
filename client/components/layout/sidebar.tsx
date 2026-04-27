"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  ArrowRightLeft,
  Brain,
  History,
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
import { useEffect, useMemo, useState, type ComponentType } from "react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

interface SidebarProps {
  portfolioId?: string;
  mobileOpen?: boolean;
  onMobileOpenChange?: (open: boolean) => void;
}

interface NavItem {
  label: string;
  href: string;
  icon: ComponentType<{ className?: string }>;
  exact?: boolean;
}

export function Sidebar({
  portfolioId,
  mobileOpen = false,
  onMobileOpenChange,
}: SidebarProps) {
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

  const mainNavItems = useMemo<NavItem[]>(
    () => [
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
              label: "Runs",
              href: `/dashboard/${portfolioId}/runs`,
              icon: History,
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
    ],
    [portfolioId]
  );

  const adminNavItems: NavItem[] =
    mounted && isReady && role === "admin"
      ? [
          {
            label: "Users",
            href: "/admin/users",
            icon: Users,
            exact: true,
          },
        ]
      : [];

  const NavLinks = ({
    mobile = false,
    onNavigate,
  }: {
    mobile?: boolean;
    onNavigate?: () => void;
  }) => (
    <>
      <nav className={cn("flex-1 space-y-1 p-2", mobile && "px-4 pb-4")}>
        {mainNavItems.map((item) => {
          const isActive = isLinkActive(item.href, item.exact);
          return (
            <Link
              key={item.href}
              href={item.href}
              prefetch
              onClick={onNavigate}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors",
                !mobile && collapsed && "justify-center",
                isActive
                  ? "bg-sidebar-accent text-sidebar-primary"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground"
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              <span
                className={cn(
                  "overflow-hidden whitespace-nowrap transition-all duration-200",
                  !mobile && collapsed ? "w-0 opacity-0" : "w-auto opacity-100"
                )}
              >
                {item.label}
              </span>
            </Link>
          );
        })}

        {adminNavItems.length > 0 && (
          <>
            {(mobile || !collapsed) && (
              <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-sidebar-foreground/50">
                Admin
              </div>
            )}
            {adminNavItems.map((item) => {
              const isActive = isLinkActive(item.href, item.exact);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  prefetch
                  onClick={onNavigate}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors",
                    !mobile && collapsed && "justify-center",
                    isActive
                      ? "bg-sidebar-accent text-sidebar-primary"
                      : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground"
                  )}
                >
                  <item.icon className="h-4 w-4 shrink-0" />
                  <span
                    className={cn(
                      "overflow-hidden whitespace-nowrap transition-all duration-200",
                      !mobile && collapsed ? "w-0 opacity-0" : "w-auto opacity-100"
                    )}
                  >
                    {item.label}
                  </span>
                </Link>
              );
            })}
          </>
        )}
      </nav>

      <div className={cn("border-t border-sidebar-border p-2", mobile && "px-4 pb-5")}>
        <Button
          variant="ghost"
          onClick={() => {
            onNavigate?.();
            logout();
          }}
          className={cn(
            "w-full gap-3 text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground",
            mobile || !collapsed ? "justify-start" : "justify-center"
          )}
        >
          <LogOut className="h-4 w-4 shrink-0" />
          <span
            className={cn(
              "overflow-hidden whitespace-nowrap transition-all duration-200",
              !mobile && collapsed ? "w-0 opacity-0" : "w-auto opacity-100"
            )}
          >
            Sign Out
          </span>
        </Button>
      </div>
    </>
  );

  return (
    <>
      <aside
        className={cn(
          "hidden h-screen flex-col border-r border-sidebar-border bg-sidebar transition-all duration-300 ease-in-out md:flex",
          collapsed ? "w-16" : "w-64"
        )}
      >
        <div className="flex h-16 items-center justify-between overflow-hidden border-b border-sidebar-border px-4">
          <Link
            href="/dashboard"
            className={cn(
              "flex items-center gap-2 overflow-hidden transition-all duration-300",
              collapsed ? "w-0 opacity-0 pointer-events-none" : "w-auto opacity-100"
            )}
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/10">
              <TrendingUp className="h-4 w-4 text-primary" />
            </div>
            <span className="whitespace-nowrap font-semibold text-sidebar-foreground">
              AlphaEngine
            </span>
          </Link>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => setCollapsed(!collapsed)}
            className="text-sidebar-foreground hover:bg-sidebar-accent"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <ChevronLeft
              className={cn("h-4 w-4 transition-transform", collapsed && "rotate-180")}
            />
          </Button>
        </div>

        <NavLinks />
      </aside>

      <Sheet open={mobileOpen} onOpenChange={onMobileOpenChange}>
        <SheetContent side="left" className="w-[88vw] max-w-sm bg-sidebar p-0">
          <SheetHeader className="border-b border-sidebar-border">
            <SheetTitle className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10">
                <TrendingUp className="h-4 w-4 text-primary" />
              </div>
              AlphaEngine
            </SheetTitle>
            <SheetDescription>
              Navigate portfolios, models, runs, and settings.
            </SheetDescription>
          </SheetHeader>
          <div className="flex min-h-0 flex-1 flex-col">
            <NavLinks mobile onNavigate={() => onMobileOpenChange?.(false)} />
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
