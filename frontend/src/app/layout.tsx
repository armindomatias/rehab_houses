import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "Rehabify - Property Investment Analysis",
  description: "Analyze property renovation costs and investment returns",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-neutral-50 text-neutral-800">
        <Navbar />
        <main>{children}</main>
        <Footer />
      </body>
    </html>
  );
}

