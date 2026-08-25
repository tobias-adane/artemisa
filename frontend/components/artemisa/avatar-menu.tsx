'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Bell, CreditCard, FileText, HelpCircle, LogOut, Sliders, User as UserIcon, Users } from 'lucide-react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { mockUser } from '@/lib/mock-data';

export function AvatarMenu() {
  const router = useRouter();
  const initials = mockUser.name
    .split(' ')
    .map((p) => p[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <Avatar>
            <AvatarFallback>{initials}</AvatarFallback>
          </Avatar>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        <DropdownMenuLabel>Mi cuenta</DropdownMenuLabel>
        <DropdownMenuItem onClick={() => router.push('/settings?tab=members')}>
          <UserIcon className="h-4 w-4" /> Perfil
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push('/settings?tab=plan')}>
          <CreditCard className="h-4 w-4" /> Suscripción
          <span className="ml-auto rounded-full bg-secondary px-2 py-0.5 text-[11px] font-semibold">Premium</span>
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push('/spaces')}>
          <Users className="h-4 w-4" /> Espacios
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push('/settings?tab=members')}>
          <Users className="h-4 w-4" /> Familia
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuLabel>Sistema</DropdownMenuLabel>
        <DropdownMenuItem onClick={() => router.push('/settings?tab=alerts')}>
          <Bell className="h-4 w-4" /> Alertas
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push('/settings?tab=members')}>
          <Sliders className="h-4 w-4" /> Instrucciones del sistema
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuLabel>Acerca de</DropdownMenuLabel>
        <DropdownMenuItem disabled>
          <FileText className="h-4 w-4" /> Términos y privacidad
        </DropdownMenuItem>
        <DropdownMenuItem disabled>
          <HelpCircle className="h-4 w-4" /> Centro de ayuda
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push('/login')}>
          <LogOut className="h-4 w-4" /> Cerrar sesión
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
