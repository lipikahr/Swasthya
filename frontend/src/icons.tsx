import type { ReactNode, SVGProps } from "react";

type IconProps = Omit<SVGProps<SVGSVGElement>, "children"> & { size?: number };

function Base({ size = 18, children, ...rest }: IconProps & { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      {children}
    </svg>
  );
}

export const CameraIcon = (p: IconProps) => (
  <Base {...p}>
    <path d="M4 8.5A2.5 2.5 0 0 1 6.5 6h1.2a1 1 0 0 0 .8-.4l.9-1.2A1 1 0 0 1 10.2 4h3.6a1 1 0 0 1 .8.4l.9 1.2a1 1 0 0 0 .8.4h1.2A2.5 2.5 0 0 1 20 8.5v8A2.5 2.5 0 0 1 17.5 19h-11A2.5 2.5 0 0 1 4 16.5v-8Z" />
    <circle cx="12" cy="12.5" r="3.3" />
  </Base>
);
export const MicIcon = (p: IconProps) => (
  <Base {...p}>
    <rect x="9" y="3" width="6" height="11" rx="3" />
    <path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21" />
  </Base>
);
export const StopIcon = (p: IconProps) => (
  <Base {...p}>
    <rect x="7" y="7" width="10" height="10" rx="2" fill="currentColor" />
  </Base>
);
export const SendIcon = (p: IconProps) => (
  <Base {...p}>
    <path d="M4 12 20 4l-4.5 16-3.5-6.5L4 12Z" />
    <path d="m12 13.5 8-9.5" />
  </Base>
);
export const ChevronLeftIcon = (p: IconProps) => (
  <Base {...p}>
    <path d="m14.5 6-6 6 6 6" />
  </Base>
);
export const ChevronRightIcon = (p: IconProps) => (
  <Base {...p}>
    <path d="m9.5 6 6 6-6 6" />
  </Base>
);
export const CalendarIcon = (p: IconProps) => (
  <Base {...p}>
    <rect x="4" y="5.5" width="16" height="14" rx="2.5" />
    <path d="M4 10h16M8.5 3.5v4M15.5 3.5v4" />
  </Base>
);
export const PlusIcon = (p: IconProps) => (
  <Base {...p}>
    <path d="M12 5v14M5 12h14" />
  </Base>
);
export const TrashIcon = (p: IconProps) => (
  <Base {...p}>
    <path d="M5 7h14M10 7V4.8h4V7M7 7l.8 12h8.4L17 7M10 11v5M14 11v5" />
  </Base>
);
export const SwapIcon = (p: IconProps) => (
  <Base {...p}>
    <path d="M5 8h12l-3-3M19 16H7l3 3" />
  </Base>
);
export const CheckIcon = (p: IconProps) => (
  <Base {...p}>
    <path d="m5 12.5 4.5 4.5L19 7.5" />
  </Base>
);
export const EditIcon = (p: IconProps) => (
  <Base {...p}>
    <path d="m4 20 1-4L16.5 4.5a2 2 0 0 1 2.8 0l.2.2a2 2 0 0 1 0 2.8L8 19l-4 1Z" />
  </Base>
);
export const SunriseIcon = (p: IconProps) => (
  <Base {...p}>
    <path d="M3 18h18M6.5 18a5.5 5.5 0 0 1 11 0M12 5v3M5 9l1.8 1.8M19 9l-1.8 1.8" />
  </Base>
);
export const SunIcon = (p: IconProps) => (
  <Base {...p}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6 7 7M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4" />
  </Base>
);
export const AppleIcon = (p: IconProps) => (
  <Base {...p}>
    <path d="M12 8.5c-1.2-1-3-1.2-4.4-.3C5.7 9.4 5.3 12 6.2 14.6 7 17 8.6 20 10.4 20c.8 0 1.1-.5 1.6-.5s.8.5 1.6.5c1.8 0 3.4-3 4.2-5.4.9-2.6.5-5.2-1.4-6.4-1.4-.9-3.2-.7-4.4.3Z" />
    <path d="M12 8.5c0-2 .8-3.6 2.5-4.5" />
  </Base>
);
export const MonitorIcon = (p: IconProps) => (
  <Base {...p}>
    <rect x="3" y="4" width="18" height="12" rx="2" />
    <path d="M8 20h8M12 16v4" />
  </Base>
);
export const MoonIcon = (p: IconProps) => (
  <Base {...p}>
    <path d="M19.5 14.5A7.5 7.5 0 0 1 9.5 4.5a7.5 7.5 0 1 0 10 10Z" />
  </Base>
);
export const FlameIcon = (p: IconProps) => (
  <Base {...p}>
    <path d="M12 3c.5 3-2.5 4.5-2.5 8a2.5 2.5 0 0 0 5 0c0-1-.4-1.7-.9-2.4 2.7 1.1 4.4 3.4 4.4 6A6 6 0 0 1 12 21a6 6 0 0 1-6-6c0-4 3.5-5.6 6-12Z" />
  </Base>
);
export const TargetIcon = (p: IconProps) => (
  <Base {...p}>
    <circle cx="12" cy="12" r="8" />
    <circle cx="12" cy="12" r="4" />
    <circle cx="12" cy="12" r="0.8" fill="currentColor" />
  </Base>
);
export const ChartIcon = (p: IconProps) => (
  <Base {...p}>
    <path d="M4 20h16M7 17v-5M12 17V7M17 17v-8" />
  </Base>
);
export const BookIcon = (p: IconProps) => (
  <Base {...p}>
    <path d="M5 4.5h10.5A3.5 3.5 0 0 1 19 8v11.5H8.5A3.5 3.5 0 0 1 5 16V4.5Z" />
    <path d="M5 16a3.5 3.5 0 0 1 3.5-3.5H19" />
  </Base>
);
export const HomeIcon = (p: IconProps) => (
  <Base {...p}>
    <path d="M4 11.5 12 5l8 6.5V19a1 1 0 0 1-1 1h-4.5v-5h-5v5H5a1 1 0 0 1-1-1v-7.5Z" />
  </Base>
);
export const ListIcon = (p: IconProps) => (
  <Base {...p}>
    <path d="M9 7h11M9 12h11M9 17h11M4.5 7h.01M4.5 12h.01M4.5 17h.01" />
  </Base>
);
export const ChatIcon = (p: IconProps) => (
  <Base {...p}>
    <path d="M5 5h14a1.5 1.5 0 0 1 1.5 1.5v8A1.5 1.5 0 0 1 19 16h-8l-4.5 3.5V16H5a1.5 1.5 0 0 1-1.5-1.5v-8A1.5 1.5 0 0 1 5 5Z" />
  </Base>
);
export const GearIcon = (p: IconProps) => (
  <Base {...p}>
    <circle cx="12" cy="12" r="3" />
    <path d="M12 3v2.2M12 18.8V21M3 12h2.2M18.8 12H21M5.6 5.6l1.6 1.6M16.8 16.8l1.6 1.6M5.6 18.4l1.6-1.6M16.8 7.2l1.6-1.6" />
  </Base>
);
export const LogoutIcon = (p: IconProps) => (
  <Base {...p}>
    <path d="M10 5H6.5A1.5 1.5 0 0 0 5 6.5v11A1.5 1.5 0 0 0 6.5 19H10M14 8l4 4-4 4M18 12H9.5" />
  </Base>
);
export const LeafIcon = (p: IconProps) => (
  <Base {...p}>
    <path d="M5 19c0-8 5-13 14-14 0 9-5 14-13 14M5 19c2-4 4-6.5 8-8.5" />
  </Base>
);
export const GlobeIcon = (p: IconProps) => (
  <Base {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M3.5 12h17M12 3.5c2.5 2.4 3.6 5.2 3.6 8.5s-1.1 6.1-3.6 8.5c-2.5-2.4-3.6-5.2-3.6-8.5S9.5 5.9 12 3.5Z" />
  </Base>
);

export const MEAL_ICONS = {
  breakfast: SunriseIcon,
  lunch: SunIcon,
  snack: AppleIcon,
  dinner: MoonIcon,
} as const;
