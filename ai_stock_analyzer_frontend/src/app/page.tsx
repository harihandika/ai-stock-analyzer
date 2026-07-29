import { redirect } from 'next/navigation';

export default function Home() {
  // Secara otomatis redirect ke halaman login
  redirect('/login');
}
