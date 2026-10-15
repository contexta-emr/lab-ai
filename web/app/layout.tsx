import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { TopBar } from "@/components/TopBar";

// The EMR's typeface. Self-hosted by next/font at build time, so opening a page
// sends no request to Google.
const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });

export const metadata: Metadata = {
  // Per-page titles land in front of this, so a browser tab says what you are
  // looking at and still says whose product it is.
  title: { default: "Lab reports · Contexta Health", template: "%s · Contexta Health" },
  description: "Drop a lab report; every test is read, matched to the patient, and charted.",
  icons: { icon: "/contexta-icon.png", apple: "/contexta-icon.png" },
  // An internal tool at a public address: keep it out of search results.
  robots: { index: false, follow: false },
};

// Next 14 wants this separately from metadata. The brand teal, so mobile
// browser chrome matches.
export const viewport: Viewport = { themeColor: "#00878a" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <TopBar />
        <main className="main">{children}</main>
      </body>
    </html>
  );
}
