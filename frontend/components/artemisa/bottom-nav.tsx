'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, Shapes, Zap, Plus } from 'lucide-react';
import { cn } from '@/lib/utils';

const ITEMS = [
  { href: '/home', label: 'Inicio', icon: Home },
  { href: '/spaces', label: 'Espacios', icon: Shapes },
  { href: '/activity', label: 'Actividad', icon: Zap },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 flex justify-center px-4 pb-6">
      <div className="flex items-center gap-2 rounded-full border border-border bg-background/95 p-2 shadow-[0_10px_34px_rgba(0,0,0,0.10)] backdrop-blur">
        {ITEMS.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + '/');
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              title={item.label}
              className={cn(
                'flex h-9 w-9 items-center justify-center rounded-full border transition-colors',
                active ? 'border-border bg-secondary text-foreground' : 'border-border text-muted-foreground hover:text-foreground'
              )}
            >
              <Icon className="h-4 w-4" strokeWidth={2} />
            </Link>
          );
        })}
        <div className="mx-1 h-5 w-px bg-border" />
        <Link
          href="/spaces?add=camera"
          title="Agregar"
          className="flex h-9 w-9 items-center justify-center rounded-full border border-border text-muted-foreground transition-colors hover:text-foreground"
        >
          <Plus className="h-4 w-4" strokeWidth={2} />
        </Link>
      </div>
    </nav>
  );
}
