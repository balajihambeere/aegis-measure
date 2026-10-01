"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  AlertsIcon,
  CalibrationIcon,
  CoverageIcon,
  LogoMark,
  ReviewIcon,
  SuitesIcon,
} from "@/components/icons";

const NAV_ITEMS = [
  { href: "/", label: "Suites", icon: SuitesIcon },
  { href: "/review", label: "Review queue", icon: ReviewIcon },
  { href: "/calibration", label: "Calibration", icon: CalibrationIcon },
  { href: "/coverage", label: "Coverage gate", icon: CoverageIcon },
  { href: "/alerts", label: "Alerts", icon: AlertsIcon },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-border bg-panel">
      <div className="flex items-center gap-2.5 border-b border-border px-5 py-5">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent/15 text-accent">
          <LogoMark className="h-5 w-5" />
        </span>
        <div className="leading-tight">
          <p className="text-[0.95rem] font-semibold tracking-tight text-ink">Aegis Measure</p>
          <p className="text-[0.7rem] font-medium uppercase tracking-wider text-faint">
            EvalOps
          </p>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 px-3 py-4">
        {NAV_ITEMS.map((item) => {
          const active = item.href === "/" ? pathname === "/" : pathname?.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`group relative flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                active
                  ? "bg-accent/12 text-ink"
                  : "text-muted hover:bg-surface hover:text-ink"
              }`}
            >
              <span
                className={`absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-accent transition-opacity ${
                  active ? "opacity-100" : "opacity-0"
                }`}
              />
              <Icon
                className={`h-[18px] w-[18px] shrink-0 ${active ? "text-accent" : "text-faint group-hover:text-muted"}`}
              />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border px-5 py-4">
        <div className="flex items-center gap-2 rounded-lg bg-surface px-3 py-2">
          <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-pass shadow-[0_0_0_3px_rgba(52,211,153,0.18)]" />
          <p className="text-xs font-medium text-muted">Development environment</p>
        </div>
      </div>
    </aside>
  );
}
