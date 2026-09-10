import type { Metadata } from 'next';
import { Inter, Instrument_Serif } from 'next/font/google';
import { I18nProvider } from '@/lib/i18n/context';
import './globals.css';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });
const instrumentSerif = Instrument_Serif({
  subsets: ['latin'],
  weight: '400',
  style: ['normal', 'italic'],
  variable: '--font-instrument-serif',
});

export const metadata: Metadata = {
  title: 'Artemisa',
  description: 'Tranquilidad para tu hogar.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es-AR" className={`${inter.variable} ${instrumentSerif.variable}`}>
      <body>
        <I18nProvider>{children}</I18nProvider>
      </body>
    </html>
  );
}
