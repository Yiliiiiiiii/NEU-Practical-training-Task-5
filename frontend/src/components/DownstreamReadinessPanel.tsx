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
    return <div className="empty-state">Execute a task to inspect downstream readiness.</div>;
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
          label={csvReady ? "CSV ready" : "CSV blocked"}
          detail="Structured business-system import"
        />
        <ReadinessItem
          ready={ragReady}
          label={ragReady ? "RAG ready" : "RAG review"}
          detail={`${chunks?.total ?? 0} source-linked chunks`}
        />
        <ReadinessItem
          ready={contractPassed}
          label={contractPassed ? "Contract passed" : "Contract pending"}
          detail="Manifest, hashes, and required artifacts"
        />
      </div>
      <p className="quiet">
        Offline adapters: export_structured_csv.py · export_rag_corpus.py ·
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
