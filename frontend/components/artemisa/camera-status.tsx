export function CameraStatus({ label, className = '' }: { label: string; className?: string }) {
  return <span className={`text-[12.5px] text-muted-foreground ${className}`}>{label}</span>;
}
