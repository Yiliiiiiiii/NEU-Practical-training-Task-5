import type { ChunksReport, PackageManifest, VerifierReport } from "../types";

export type DownstreamReadinessPanelProps = {
  manifest: PackageManifest | null;
  chunks: ChunksReport | null;
  verifier: VerifierReport | null;
};

export function DownstreamReadinessPanel({
  manifest,
  chunks,
  verifier
}: DownstreamReadinessPanelProps) {
  if (!manifest) {
    return <div className="empty-state">执行 Task 后可查看下游就绪度。</div>;
  }
  const paths = new Set(manifest.files.map((file) => file.path));
  const csvReady = paths.has("content.json") || paths.has("canonical.json");
  const ragReady =
    paths.has("chunks.jsonl") &&
    Boolean(chunks?.items.length) &&
    chunks!.items.every(
      (chunk) => Boolean(chunk.source_block_ids?.length) || Boolean(chunk.source_links?.length)
    );
  const contractPassed = verifier?.passed === true;

  return (
    <div className="evidence-panel downstream-readiness-panel">
      <div className="readiness-grid">
        <ReadinessItem
          ready={csvReady}
          label={csvReady ? "CSV 已就绪" : "CSV 未就绪"}
          detail="结构化业务系统导入"
        />
        <ReadinessItem
          ready={ragReady}
          label={ragReady ? "RAG 已就绪" : "RAG 待 Review"}
          detail={`${chunks?.total ?? 0} 个带来源链接的 Chunk`}
        />
        <ReadinessItem
          ready={contractPassed}
          label={contractPassed ? "契约已通过" : "契约待验证"}
          detail="Manifest、哈希与必需产物"
        />
      </div>
      <p className="quiet">
        离线适配脚本：export_structured_csv.py · export_rag_corpus.py ·
        verify_downstream_contract.py
      </p>
    </div>
  );
}

function ReadinessItem({
  ready,
  label,
  detail
}: {
  ready: boolean;
  label: string;
  detail: string;
}) {
  return (
    <div className={ready ? "readiness-item readiness-pass" : "readiness-item"}>
      <strong>{label}</strong>
      <span>{detail}</span>
    </div>
  );
}
