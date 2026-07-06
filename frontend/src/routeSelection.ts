type RouteCandidate = {
  schema_id: string;
  template_id: string;
};

type RouteSelectionInput = {
  selected_schema_id: string | null;
  selected_template_id: string | null;
  review_required: boolean;
  candidates: RouteCandidate[];
};

export type ResolvedRouteSelection = {
  schemaId: string;
  templateId: string;
  canCreate: boolean;
  requiresConfirmation: boolean;
};

export function resolveRouteSelection(
  route: RouteSelectionInput,
  schemaOverride: string,
  reviewConfirmed: boolean
): ResolvedRouteSelection {
  const overrideCandidate = route.candidates.find(
    (candidate) => candidate.schema_id === schemaOverride
  );
  const schemaId = overrideCandidate?.schema_id ?? route.selected_schema_id ?? "";
  const templateId = overrideCandidate?.template_id ?? route.selected_template_id ?? "";
  const requiresConfirmation = route.review_required && !reviewConfirmed;
  return {
    schemaId,
    templateId,
    canCreate: Boolean(schemaId && templateId && !requiresConfirmation),
    requiresConfirmation
  };
}
