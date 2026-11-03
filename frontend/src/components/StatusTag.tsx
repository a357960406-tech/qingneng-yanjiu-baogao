export function StatusTag({ status }: { status: string }) {
  const map: Record<string, { label: string; className: string }> = {
    可用: { label: "可用", className: "bg-status-ok/10 text-status-ok" },
    无文字: { label: "无文字，检索不到", className: "bg-status-warn/10 text-status-warn" },
    失败: { label: "失败", className: "bg-status-danger/10 text-status-danger" },
    待确认大纲: { label: "待确认大纲", className: "bg-status-info/10 text-status-info" },
    写作中: { label: "写作中", className: "bg-status-info/10 text-status-info" },
    已完成: { label: "已完成", className: "bg-status-ok/10 text-status-ok" },
    通过: { label: "通过", className: "bg-status-ok/10 text-status-ok" },
    待人工: { label: "待人工", className: "bg-status-warn/10 text-status-warn" },
  };
  const item = map[status] ?? { label: status, className: "bg-control-gray text-slate" };
  return (
    <span className={`inline-block rounded-tag px-2.5 py-0.5 text-xs font-medium ${item.className}`}>
      {item.label}
    </span>
  );
}
