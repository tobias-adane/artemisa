import { AvatarMenu } from '@/components/artemisa/avatar-menu';

export function PageHeader({ title, right }: { title: string; right?: React.ReactNode }) {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-transparent bg-background/85 px-5 backdrop-blur">
      <AvatarMenu />
      <div className="rounded-full bg-background px-4 py-2 text-xs font-medium">{title}</div>
      <div className="flex w-8 justify-end">{right}</div>
    </header>
  );
}
