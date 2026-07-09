# Schema Validation Localization

- Case count: 6
- Localization rate: 1.000

| Case | Expected path | Localized paths | Passed |
| --- | --- | --- | --- |
| missing_required | issuer | issuer | True |
| wrong_date_format | publish_date | publish_date | True |
| wrong_enum | doc_type | doc_type | True |
| wrong_type | title | title | True |
| bad_nested_path | package.manifest.checksum | package.manifest.checksum | True |
| invalid_package_artifact | package.manifest | package.manifest | True |
