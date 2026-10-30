type LogoProps = {
  className?: string;
  size?: number;
};

export function Logo({ className = "", size = 42 }: LogoProps) {
  return (
    <img
      className={className ? `brand-logo ${className}` : "brand-logo"}
      src="/logo.png"
      alt=""
      width={size}
      height={size}
      decoding="async"
    />
  );
}
