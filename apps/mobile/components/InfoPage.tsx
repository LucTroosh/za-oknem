import type { ReactNode } from "react";

import PageHeader from "./PageHeader";
import Screen from "./Screen";

// A settings sub-page: back + title + content cards.
export default function InfoPage({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Screen padTop gap={16}>
      <PageHeader title={title} backLabel="Ustawienia" />
      {children}
    </Screen>
  );
}
