# Optional Raw Document Upstream Example

This directory contains a small text-layer PDF and its generated block-list
External UIR. The example is offline tooling, not a production file-upload
route and not an OCR service.

Run the Docling entry point:

```powershell
python scripts\upstream_docling_to_external_uir.py `
  examples\raw_upstream\sample_policy.pdf `
  --out examples\raw_upstream\sample_policy_external_uir.json `
  --report reports\raw_upstream\sample_policy_report.json
```

Docling is optional. When it is not installed, this text-layer PDF uses the
existing deterministic PyMuPDF extractor. A scanned PDF without a usable text
layer is rejected as `unsupported_scanned_pdf`; the tool does not perform OCR.

The generated JSON must still be converted, previewed, imported, and explicitly
used to create a task through the existing External UIR workflow.
