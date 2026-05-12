/**
 * Index route — redirects to the appropriate screen
 * based on auth state. The _layout.tsx handles the actual redirect,
 * this just renders nothing while it happens.
 */

import { Redirect } from "expo-router";
import { useAuth } from "@/lib/auth";

export default function IndexRoute() {
  const { isAuthenticated } = useAuth();

  if (isAuthenticated) {
    return <Redirect href="/(tabs)/dashboard" />;
  }

  return <Redirect href="/(auth)/login" />;
}
