const statusLabels: Record<string, string> = {
  completed: "已完成",
  verified: "已验证",
  review_required: "需要复核",
  failed: "失败",
  running: "进行中",
  pending: "待处理",
  draft: "草案",
  active: "已激活",
  archived: "已归档",
  blocked: "已阻断",
  unmapped: "未映射",
  unverified: "未验证",
  unknown: "未知"
};

export function formatStatus(status: string): string {
  return statusLabels[status.toLowerCase()] ?? status;
}
