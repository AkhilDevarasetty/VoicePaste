type IconProps = {
  className?: string;
};

const base = "h-[18px] w-[18px]";

export function GridIcon({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <rect x="2" y="2" width="6" height="6" rx="2" stroke="currentColor" strokeWidth="1.8" />
      <rect x="12" y="2" width="6" height="6" rx="2" stroke="currentColor" strokeWidth="1.8" />
      <rect x="2" y="12" width="6" height="6" rx="2" stroke="currentColor" strokeWidth="1.8" />
      <rect x="12" y="12" width="6" height="6" rx="2" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

export function ListIcon({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <rect x="3" y="3" width="4" height="4" rx="1.2" stroke="currentColor" strokeWidth="1.8" />
      <path d="M10 5h7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <rect x="3" y="13" width="4" height="4" rx="1.2" stroke="currentColor" strokeWidth="1.8" />
      <path d="M10 15h7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export function MicrophoneIcon({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <rect x="7" y="2.5" width="6" height="10" rx="3" stroke="currentColor" strokeWidth="1.8" />
      <path d="M4.5 9.5a5.5 5.5 0 0 0 11 0" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M10 15v2.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M6.5 17.5h7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export function SettingsIcon({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path
        d="M8.1 2.6h3.8l.6 2a5.7 5.7 0 0 1 1.5.9L16 4.8l1.9 3.3-1.5 1.5c.1.5.1 1 0 1.6l1.5 1.5-1.9 3.3-2-.7a5.7 5.7 0 0 1-1.5.9l-.6 2H8.1l-.6-2a5.7 5.7 0 0 1-1.5-.9l-2 .7-1.9-3.3 1.5-1.5a5 5 0 0 1 0-1.6L2.1 8.1 4 4.8l2 .7a5.7 5.7 0 0 1 1.5-.9l.6-2Z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <circle cx="10" cy="10" r="2.4" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

export function CopyIcon({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <rect x="7" y="4" width="9" height="11" rx="2" stroke="currentColor" strokeWidth="1.8" />
      <path d="M4.5 12V6.5A2.5 2.5 0 0 1 7 4h5.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export function RetryIcon({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M15.5 8a5.5 5.5 0 1 0 1 4.4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M12.8 4.6h3.3v3.3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function TrashIcon({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M4.5 6h11" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M7.5 6V4.6A1.6 1.6 0 0 1 9.1 3h1.8a1.6 1.6 0 0 1 1.6 1.6V6" stroke="currentColor" strokeWidth="1.8" />
      <path d="M6.5 6l.7 9a2 2 0 0 0 2 1.8h1.6a2 2 0 0 0 2-1.8l.7-9" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export function ChevronRightIcon({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="m8 5 5 5-5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function SparkIcon({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M10 2.5 11.5 8 17 10l-5.5 2-1.5 5.5L8.5 12 3 10l5.5-2L10 2.5Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  );
}

export function PlusIcon({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M10 4.5v11" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M4.5 10h11" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}
