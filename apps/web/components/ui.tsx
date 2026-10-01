import { ButtonHTMLAttributes, ReactNode } from "react";
import Link from "next/link";
import { ArrowLeftIcon, DotIcon } from "@/components/icons";

export type Tone = "pass" | "fail" | "warn" | "neutral";

const toneDot: Record<Tone, string> = {
  pass: "text-pass",
  fail: "text-fail",
  warn: "text-warn",
  neutral: "text-faint",
};

const toneClasses: Record<Tone, string> = {
  pass: "bg-pass/12 text-pass ring-1 ring-inset ring-pass/20",
  fail: "bg-fail/12 text-fail ring-1 ring-inset ring-fail/20",
  warn: "bg-warn/12 text-warn ring-1 ring-inset ring-warn/20",
  neutral: "bg-muted/10 text-muted ring-1 ring-inset ring-border-strong/60",
};

export function Badge({ tone, children }: { tone: Tone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold tracking-tight ${toneClasses[tone]}`}
    >
      <DotIcon className={`h-1.5 w-1.5 ${toneDot[tone]}`} />
      {children}
    </span>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`mb-4 rounded-2xl border border-border bg-panel p-5 shadow-card ${className}`}>
      {children}
    </div>
  );
}

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" }) {
  const base =
    "inline-flex items-center justify-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:shadow-ring disabled:cursor-not-allowed disabled:opacity-50";
  const variantClasses =
    variant === "primary"
      ? "bg-accent text-white shadow-[0_1px_0_0_rgba(255,255,255,0.12)_inset] hover:bg-accent-hover"
      : "border border-border-strong bg-surface text-ink hover:bg-panel-hover";
  return <button className={`${base} ${variantClasses} ${className}`} {...props} />;
}

export function Label({ children, htmlFor }: { children: ReactNode; htmlFor?: string }) {
  return (
    <label
      htmlFor={htmlFor}
      className="mb-1.5 mt-4 block text-[0.7rem] font-semibold uppercase tracking-wider text-faint"
    >
      {children}
    </label>
  );
}

const fieldClasses =
  "w-full rounded-lg border border-border bg-bg-raised px-3 py-2 text-sm text-ink placeholder:text-faint transition-colors focus:border-accent focus:outline-none focus:shadow-ring";

export function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className={fieldClasses} {...props} />;
}

export function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={fieldClasses} {...props} />;
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={fieldClasses} {...props} />;
}

export function AnswerBlock({ children }: { children: ReactNode }) {
  return (
    <div className="my-1 whitespace-pre-wrap rounded-lg border border-border bg-bg-raised py-2.5 pl-3.5 pr-3 text-sm leading-relaxed text-ink/90 shadow-[inset_2px_0_0_0_#323748]">
      {children}
    </div>
  );
}

export function ErrorBanner({ children }: { children: ReactNode }) {
  return (
    <div className="mb-4 flex items-start gap-2.5 rounded-lg border border-fail/30 bg-fail/10 px-4 py-3 text-sm text-fail">
      <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-fail" />
      {children}
    </div>
  );
}

export function Muted({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <p className={`text-sm text-muted ${className}`}>{children}</p>;
}

export function Table({ children }: { children: ReactNode }) {
  return (
    <div className="mt-4 overflow-x-auto rounded-xl border border-border bg-panel shadow-card">
      <table className="w-full min-w-full border-collapse">{children}</table>
    </div>
  );
}

export function TableBody({ children }: { children: ReactNode }) {
  return (
    <tbody className="[&_tr:last-child_td]:border-b-0 [&_tr:hover]:bg-surface/50 [&_td]:border-b [&_td]:border-border [&_td]:px-4 [&_td]:py-3 [&_td]:text-sm [&_tr]:transition-colors">
      {children}
    </tbody>
  );
}

export function TableHead({ columns }: { columns: string[] }) {
  return (
    <thead>
      <tr className="bg-panel-hover">
        {columns.map((c) => (
          <th
            key={c}
            className="border-b border-border px-4 py-2.5 text-left text-[0.7rem] font-semibold uppercase tracking-wider text-faint"
          >
            {c}
          </th>
        ))}
      </tr>
    </thead>
  );
}

export function PageHeader({
  title,
  description,
  action,
  back,
}: {
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  back?: { href: string; label: string };
}) {
  return (
    <div className="mb-6 border-b border-border pb-5">
      {back && <BackLink href={back.href}>{back.label}</BackLink>}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-[1.375rem] font-semibold tracking-tight text-ink">{title}</h1>
          {description && <Muted className="mt-1.5 max-w-2xl">{description}</Muted>}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
    </div>
  );
}

export function BackLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="mb-3 inline-flex items-center gap-1.5 text-sm font-medium text-muted transition-colors hover:text-ink"
    >
      <ArrowLeftIcon className="h-3.5 w-3.5" />
      {children}
    </Link>
  );
}

export function SectionTitle({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-3 mt-8 flex items-center justify-between first:mt-0">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-faint">{children}</h2>
      {action}
    </div>
  );
}

export function StatCard({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: ReactNode;
  tone?: Tone;
}) {
  const valueTone: Record<Tone, string> = {
    pass: "text-pass",
    fail: "text-fail",
    warn: "text-warn",
    neutral: "text-ink",
  };
  return (
    <div className="rounded-2xl border border-border bg-panel p-4 shadow-card">
      <p className="text-[0.7rem] font-semibold uppercase tracking-wider text-faint">{label}</p>
      <p className={`mt-1.5 text-2xl font-semibold tracking-tight ${valueTone[tone]}`}>{value}</p>
    </div>
  );
}

export function StatGrid({ children }: { children: ReactNode }) {
  return <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">{children}</div>;
}

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-border-strong bg-transparent px-4 py-8 text-center">
      <Muted>{children}</Muted>
    </div>
  );
}
