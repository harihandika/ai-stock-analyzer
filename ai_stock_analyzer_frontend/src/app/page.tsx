import { redirect } from 'navigation';

// Karena ini adalah app Next.js versi 14/15, kita menggunakan redirect dari next/navigation
// Tapi pastikan menggunakan redirect dari 'next/navigation'
import { redirect as nextRedirect } from 'next/navigation';

export default function Home() {
  // Secara otomatis redirect ke halaman login
  nextRedirect('/login');
}
