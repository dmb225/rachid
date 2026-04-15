"use client";

import { ChatContainer, ConversationSidebar } from "@/components/chat";

export default function ChatPage() {
  return (
    <div className="-m-3 flex min-h-0 flex-1 sm:-m-6">
      <ConversationSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="min-h-0 flex-1">
          <ChatContainer />
        </div>
      </div>
    </div>
  );
}
