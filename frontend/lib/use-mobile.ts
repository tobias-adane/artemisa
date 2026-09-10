'use client';

import { useEffect, useState } from 'react';

const MOBILE_BREAKPOINT = 768;

/** Espeja el breakpoint de design-reference/*.dc.html (isMobile: window.innerWidth < 768). */
export function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

  return isMobile;
}
