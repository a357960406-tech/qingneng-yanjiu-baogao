"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ReportItem } from "@/lib/types";
import { StatusTag } from "@/components/StatusTag";

export default function HomePage() {
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .listReports()
      .then((d) => setReports(d.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl font-bold">我的报告</h1>
        <p className="mt-1 text-sm opacity-70">把项目资料写成可研报告初稿，数字不能错。</p>
      </div>

      {loading && <p className="text-sm opacity-70">加载中…</p>}
      {!loading && error && (
        <div className="rounded-card border border-barn-red/40 bg-barn-red/10 p-4 text-sm text-barn-red">
          加载失败：{error}
        </div>
      )}
      {!loading && !error && reports.length === 0 && (
        <div className="rounded-card border border-dark-cocoa/15 bg-cream-parchment p-8 text-center">
          <p className="font-display text-lg">还没有报告</p>
          <p className="mt-1 text-sm opacity-70">先到「资料库」上传项目资料，再来创建报告。</p>
        </div>
      )}
      {!loading && !error && reports.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {reports.map((r) => (
            <div key={r.id} className="rounded-card border border-dark-cocoa/20 bg-cream-parchment p-4">
              <div className="flex items-start justify-between gap-2">
                <h2 className="font-display text-lg leading-snug">{r.title}</h2>
                <StatusTag status={r.status} />
              </div>
              <p className="mt-2 text-sm opacity-70">
                目标字数 {r.target_words} · {r.outline_confirmed ? "大纲已确认" : "大纲未确认"}
              </p>
              <p className="mt-1 text-xs opacity-50">{r.created_at}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
