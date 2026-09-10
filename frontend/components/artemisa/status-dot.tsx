export function StatusDot({ color, size = 8, className = '' }: { color: string; size?: number; className?: string }) {
  return (
    <span
      className={`inline-block flex-none rounded-full ${className}`}
      style={{ width: size, height: size, backgroundColor: color }}
    />
  );
}
