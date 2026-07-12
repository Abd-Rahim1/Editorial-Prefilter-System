import { useEffect } from 'react';
import { useRouter } from 'next/router';

export default function EditorIndex() {
  const router = useRouter();
  useEffect(() => {
    router.replace('/editor/queue');
  }, [router]);
  return null;
}
