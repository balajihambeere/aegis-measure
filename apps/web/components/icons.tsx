import { SVGProps } from "react";

export type IconProps = SVGProps<SVGSVGElement>;

const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export function LogoMark(props: IconProps) {
  return (
    <svg {...base} strokeWidth={1.6} {...props}>
      <path d="M12 2.5l7.5 3v5.2c0 4.86-3.2 8.9-7.5 10.8-4.3-1.9-7.5-5.94-7.5-10.8V5.5l7.5-3z" />
      <path d="M8.75 12.25l2.25 2.25 4.25-4.5" />
    </svg>
  );
}

export function SuitesIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M12 3l8.5 4.5L12 12 3.5 7.5 12 3z" />
      <path d="M3.5 12l8.5 4.5 8.5-4.5" />
      <path d="M3.5 16.5L12 21l8.5-4.5" />
    </svg>
  );
}

export function ReviewIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <rect x="5" y="3.5" width="14" height="17" rx="2" />
      <path d="M9 3.5V3a1.5 1.5 0 013 0v.5" />
      <path d="M8.5 12l2.2 2.2L15.5 10" />
    </svg>
  );
}

export function CalibrationIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M4.5 16a7.5 7.5 0 1115 0" />
      <path d="M12 16l3.5-4.2" />
      <circle cx="12" cy="16" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function CoverageIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M12 3l7 2.8v5.1c0 4.5-3 8.3-7 9.6-4-1.3-7-5.1-7-9.6V5.8L12 3z" />
      <path d="M12 8v4.5" />
      <circle cx="12" cy="15.2" r="0.9" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function AlertsIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M6 10a6 6 0 1112 0c0 4 1.5 5.5 1.5 5.5h-15S6 14 6 10z" />
      <path d="M10.3 19a1.8 1.8 0 003.4 0" />
    </svg>
  );
}

export function ArrowLeftIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M19 12H5" />
      <path d="M11 6l-6 6 6 6" />
    </svg>
  );
}

export function PlusIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </svg>
  );
}

export function PlayIcon(props: IconProps) {
  return (
    <svg {...base} fill="currentColor" stroke="none" {...props}>
      <path d="M7 4.7c0-.9 1-1.5 1.8-1l10 6.3a1.2 1.2 0 010 2l-10 6.3c-.8.5-1.8-.1-1.8-1V4.7z" />
    </svg>
  );
}

export function CheckCircleIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="12" r="8.25" />
      <path d="M8.5 12.3l2.3 2.3 4.7-5" />
    </svg>
  );
}

export function XCircleIcon(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="12" r="8.25" />
      <path d="M9.5 9.5l5 5" />
      <path d="M14.5 9.5l-5 5" />
    </svg>
  );
}

export function DotIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 8 8" fill="currentColor" {...props}>
      <circle cx="4" cy="4" r="4" />
    </svg>
  );
}
