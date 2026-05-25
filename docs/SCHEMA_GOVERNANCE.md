# TANTRA Schema Governance Declaration

## 1. Canonical Ownership
All schemas are centrally owned and enforced in `shared_canonical_schemas/registry.py`. Local forks or duplication of `TantraInputContract`, `TantraOutputContract`, `PropagationInput`, or `PropagationOutput` are strictly prohibited.

## 2. Zero Transformation Rule
The `TantraOutputContract` produced by the KESHAV Engine must be consumed byte-for-byte by the RAJYA (Decision), Sarathi (Enforcement), Core (Execution), and Bucket (Truth) layers. No adapter, renaming, or structural mutation is permitted.

## 3. Strict Forbidding
All models specify `model_config = ConfigDict(extra="forbid")`. Unrecognized fields will cause immediate fail-closed pipeline rejections.

## 4. Operational Maintenance
The incoming maintainer (Rajaryan Verma) is responsible for ensuring that changes to these contracts are coordinated across all 5 participating repositories:
- `KESHAV-4-main`
- `keshavrRedesign-main`
- `Sarathi`
- `deterministic_validation_engine`
- `keshav_validation_engine`

## 5. Trace Mutability
`trace_id` is an immutable proof identifier. Any process modifying `trace_id` violates the structural integrity of the pipeline.
