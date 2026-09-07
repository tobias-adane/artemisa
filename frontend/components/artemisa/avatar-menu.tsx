'use client';

import { useRouter } from 'next/navigation';
import { CreditCard, FileText, Folders, HelpCircle, LogOut, Settings2, UserRound } from 'lucide-react';
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
          <Avatar className="h-7 w-7">
            <AvatarFallback className="text-[11px]">{initials}</AvatarFallback>
          </Avatar>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-[214px]">
        <DropdownMenuLabel>Mi cuenta</DropdownMenuLabel>
        <DropdownMenuItem onClick={() => router.push('/settings?tab=perfil')}>
          <UserRound className="h-4 w-4" /> Perfil
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push('/settings?tab=suscripcion')}>
          <CreditCard className="h-4 w-4" /> Subscripción
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push('/settings')}>
          <Settings2 className="h-4 w-4" /> Configuración
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => router.push('/settings?tab=recursos')}>
          <Folders className="h-4 w-4" /> Recursos
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push('/settings?tab=terminos')}>
          <FileText className="h-4 w-4" /> Términos & Privacidad
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push('/settings?tab=ayuda')}>
          <HelpCircle className="h-4 w-4" /> Ayuda
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push('/login')}>
          <LogOut className="h-4 w-4" /> Cerrar sesión
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
