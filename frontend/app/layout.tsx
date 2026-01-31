import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Providers from './providers';
import Layout from '@/components/Layout';
import MedicalDisclaimer from '@/components/MedicalDisclaimer';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'AI-Powered Drug Discovery Platform',
  description:
    'Transform disease queries into ranked drug candidates using AI and biomedical databases',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          <Layout>{children}</Layout>
          <MedicalDisclaimer />
        </Providers>
      </body>
    </html>
  );
}
