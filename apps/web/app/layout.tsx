import type { Metadata } from "next";
import Sidebar from "@/components/Sidebar";
import "./globals.css";

export const metadata: Metadata = {
  title: "Aegis Measure",
  description: "EvalOps platform for continuous AI-quality evaluation — the Measure stage.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex min-h-screen bg-bg font-sans text-ink">
        <Sidebar />
        <div
          className="flex-1"
          style={{
            backgroundImage:
              "radial-gradient(1100px circle at 15% -10%, rgba(91,124,250,0.08), transparent 55%)",
          }}
        >
          <main className="mx-auto max-w-6xl px-10 py-10">{children}</main>
        </div>
      </body>
    </html>
  );
}
