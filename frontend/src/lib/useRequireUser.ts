"use client";

import { useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { useActiveUser, useHydrated, type User } from "@/state/store";

/** Returns the active user, or redirects to the user picker once hydrated. */
export function useRequireUser(): { user: User | null; ready: boolean } {
  const user = useActiveUser();
  const hydrated = useHydrated();
  const router = useRouter();

  useEffect(() => {
    if (hydrated && !user) router.replace("/start");
  }, [hydrated, user, router]);

  return { user, ready: hydrated && user !== null };
}
