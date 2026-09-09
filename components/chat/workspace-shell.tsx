"use client";

import { usePathname } from "next/navigation";
import { ActiveChatProvider } from "@/hooks/use-active-chat";
import { ChatShell } from "./shell";

export function WorkspaceShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  if (pathname.startsWith("/knowledge") || pathname.startsWith("/traces")) {
    return <>{children}</>;
  }

  return (
    <>
      <ActiveChatProvider>
        <ChatShell />
      </ActiveChatProvider>
      {children}
    </>
  );
}
