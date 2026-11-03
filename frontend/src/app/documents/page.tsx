"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { DocumentItem } from "@/lib/types";
import { Button } from "@/components/Button";
import { StatusTag } from "@/components/StatusTag";

export default function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  function load() {
    api
      .listDocuments()
      .then((d) => setDocs(d.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  async function onUpload(files: FileList | null) {
    if (!files || files.length === 0) return;
    setUploading(true);
    setError("");
    setNotice("");
    for (const f of Array.from(files)) {
      try {
        await api.uploadDocument(f);
        setNotice((n) => `${n}已上传：${f.name}；`);
      } catch (e) {
        setError((e as Error).message);
      }
    }
    setUploading(false);
    if (fileRef.current) fileRef.current.value = "";
    load();
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl font-bold">资料库</h1>
        <p className="mt-1 text-sm opacity-70">支持 PDF、Word、Markdown、TXT；单个文件不超过 100M。</p>
      </div>

      <input
        ref={fileRef}
        type="file"
        multiple
        accept=".pdf,.docx,.md,.txt"
        className="hidden"
        onChange={(e) => onUpload(e.target.files)}
      />
      <div className="mb-6 flex items-center gap-3">
        <Button onClick={() => fileRef.current?.click()} disabled={uploading}>
          {uploading ? "上传中…" : "上传资料"}
        </Button>
        {notice && <span className="text-sm text-sage-green">{notice}</span>}
      </div>

      {loading && <p className="text-sm opacity-70">加载中…</p>}
      {!loading && error && (
        <div className="rounded-card border border-barn-red/40 bg-barn-red/10 p-4 text-sm text-barn-red">
          {error}
        </div>
      )}
      {!loading && !error && docs.length === 0 && (
        <div className="rounded-card border border-dark-cocoa/15 bg-cream-parchment p-8 text-center">
          <p className="font-display text-lg">资料库还是空的</p>
          <p className="mt-1 text-sm opacity-70">点「上传资料」把项目文档放进来。</p>
        </div>
      )}
      {!loading && !error && docs.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-dark-cocoa/20 text-left">
                <th className="py-2 pr-4">文件名</th>
                <th className="py-2 pr-4">类型</th>
                <th className="py-2 pr-4">状态</th>
                <th className="py-2 pr-4">切段</th>
                <th className="py-2 pr-4">字数</th>
                <th className="py-2">上传时间</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id} className="border-b border-dark-cocoa/10 align-top">
                  <td className="py-2 pr-4">{d.filename}</td>
                  <td className="py-2 pr-4 uppercase">{d.file_type}</td>
                  <td className="py-2 pr-4">
                    <StatusTag status={d.status} />
                    {d.error_reason && <p className="mt-1 text-xs opacity-70">{d.error_reason}</p>}
                  </td>
                  <td className="py-2 pr-4">{d.chunk_count}</td>
                  <td className="py-2 pr-4">{d.char_count}</td>
                  <td className="py-2 text-xs opacity-60">{d.created_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
