import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "可研报告生成Agent",
  description: "氢能项目可研报告生成工具",
};

const nav = [
  { href: "/", label: "首页" },
  { href: "/documents", label: "资料库" },
];

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN" className="h-full">
      <body className="min-h-full flex flex-col">
        <header className="border-b border-hairline-silver bg-gallery-white">
          <div className="mx-auto flex max-w-6xl items-center gap-8 px-4 py-3">
            <Link href="/" className="font-display text-lg font-semibold tracking-tight text-ink">
              可研报告生成 Agent
            </Link>
            <nav className="flex items-center gap-6 text-sm text-slate">
              {nav.map((n) => (
                <Link key={n.href} href={n.href} className="hover:text-ink">
                  {n.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
