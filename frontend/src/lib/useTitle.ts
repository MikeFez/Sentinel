import { useEffect } from 'react';

/** Set the browser tab title while a page is shown. */
export function useTitle(title: string | null | undefined) {
  useEffect(() => {
    document.title = title ? `${title} · Sentinel` : 'Sentinel';
  }, [title]);
}
