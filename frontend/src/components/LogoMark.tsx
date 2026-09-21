interface LogoMarkProps {
  size?: number;
}

export function LogoMark({ size = 42 }: LogoMarkProps) {
  return (
    <div
      className="logo-mark"
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      <svg viewBox="0 0 48 48" role="img">
        <path
          d="M13 10.5h13.5c4.7 0 8.5 3.8 8.5 8.5v18.5H21.5c-4.7 0-8.5-3.8-8.5-8.5V10.5Z"
          fill="currentColor"
          opacity=".24"
        />
        <path
          d="M9 7h14c5.5 0 10 4.5 10 10v19H19c-5.5 0-10-4.5-10-10V7Z"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.6"
          strokeLinejoin="round"
        />
        <path
          d="M17 16h9M17 22h9M17 28h5"
          stroke="currentColor"
          strokeWidth="2.6"
          strokeLinecap="round"
        />
        <circle cx="34.5" cy="10.5" r="4.5" fill="#f3b65b" />
      </svg>
    </div>
  );
}
