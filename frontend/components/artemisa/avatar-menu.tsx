'use client';

import { useRouter } from 'next/navigation';
import { CreditCard, FileText, Folders, Globe, HelpCircle, LogOut, Settings2, UserRound } from 'lucide-react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { mockUser } from '@/lib/mock-data';
import { useI18n } from '@/lib/i18n/context';

export function AvatarMenu() {
  const router = useRouter();
  const { dict, locale, setLocale } = useI18n();
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
        <DropdownMenuLabel>{dict.avatarMenu.myAccount}</DropdownMenuLabel>
        <DropdownMenuItem onClick={() => router.push('/settings?tab=perfil')}>
          <UserRound className="h-4 w-4" /> {dict.avatarMenu.profile}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push('/settings?tab=suscripcion')}>
          <CreditCard className="h-4 w-4" /> {dict.avatarMenu.subscription}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push('/settings')}>
          <Settings2 className="h-4 w-4" /> {dict.avatarMenu.settings}
        </DropdownMenuItem>
        <DropdownMenuSub>
          <DropdownMenuSubTrigger>
            <Globe className="h-4 w-4" /> {dict.avatarMenu.language}
          </DropdownMenuSubTrigger>
          <DropdownMenuSubContent>
            <DropdownMenuItem onClick={() => setLocale('es')}>
              {dict.settings.idioma.spanish} {locale === 'es' && '✓'}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setLocale('en')}>
              {dict.settings.idioma.english} {locale === 'en' && '✓'}
            </DropdownMenuItem>
          </DropdownMenuSubContent>
        </DropdownMenuSub>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => router.push('/settings?tab=recursos')}>
          <Folders className="h-4 w-4" /> {dict.avatarMenu.resources}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push('/settings?tab=terminos')}>
          <FileText className="h-4 w-4" /> {dict.avatarMenu.terms}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push('/settings?tab=ayuda')}>
          <HelpCircle className="h-4 w-4" /> {dict.avatarMenu.help}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push('/login')}>
          <LogOut className="h-4 w-4" /> {dict.avatarMenu.logout}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
