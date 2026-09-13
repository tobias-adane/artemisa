import { Sofa, UtensilsCrossed, DoorOpen, BedDouble, Trees, Briefcase, GalleryHorizontalEnd, type LucideIcon } from 'lucide-react';

/** Ícono por espacio para el chip de contexto del composer — ver components/artemisa/chat-composer.tsx. */
export const SPACE_ICONS: Record<string, LucideIcon> = {
  living: Sofa,
  kitchen: UtensilsCrossed,
  entrance: DoorOpen,
  bedroom: BedDouble,
  backyard: Trees,
  office: Briefcase,
};

export function iconForSpace(spaceId: string): LucideIcon {
  return SPACE_ICONS[spaceId] ?? GalleryHorizontalEnd;
}
