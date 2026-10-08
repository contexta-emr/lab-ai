import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

export const metadata: Metadata = {
  // Per-page titles land in front of this, so a browser tab says what you are
  // looking at and still says whose product it is.
  title: { default: "Lab IDP · Contexta Health", template: "%s · Contexta Lab IDP" },
  description: "Read a lab report, find the patient, store the results.",
  icons: { icon: "/contexta-icon.png", apple: "/contexta-icon.png" },
};

// Next 14 wants this separately from metadata, and warns on every render if it
// is not. The brand teal, so mobile browser chrome matches the rail.
export const viewport: Viewport = { themeColor: "#00878a" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <Sidebar />
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
