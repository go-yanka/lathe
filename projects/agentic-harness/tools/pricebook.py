# hand-maintained DATA table (operating contract #12 L3) — versioned model->list-price map. Not decision
# logic: the cost MATH lives in the pinned manifest_core.imputed_cost; this file only supplies the numbers.
# Update PRICEBOOK_VERSION whenever a price changes so manifests are auditable against the book they used.
PRICEBOOK_VERSION = "2026-06-24"

# USD per 1M tokens (list price). billing_mode: how the endpoint is actually paid for —
# 'subscription' (flat-rate CLI proxy: real $0, imputed = list), 'local-free' (own hardware), 'metered'.
PRICES = {
    "claude-opus-4-8":    {"in_per_mtok": 5.00, "out_per_mtok": 25.00},
    "claude-sonnet-5":    {"in_per_mtok": 3.00, "out_per_mtok": 15.00},
    "claude-haiku-4-5":   {"in_per_mtok": 1.00, "out_per_mtok": 5.00},
    "sonnet":             {"in_per_mtok": 3.00, "out_per_mtok": 15.00},   # proxy alias
    "opus":               {"in_per_mtok": 5.00, "out_per_mtok": 25.00},   # proxy alias
    "haiku":              {"in_per_mtok": 1.00, "out_per_mtok": 5.00},    # proxy alias
    "local":              {"in_per_mtok": 0.00, "out_per_mtok": 0.00},
}

BILLING_MODE = {
    "claude": "subscription",       # CLI proxy on a flat plan: marginal cost $0, imputed at list
    "openai-local": "local-free",
    "ollama": "local-free",
}


def price_for(model_id):
    """List price for a model id; unknown -> zeros (never raises, never blocks a manifest)."""
    try:
        p = PRICES.get(str(model_id))
        if isinstance(p, dict):
            return {"in_per_mtok": float(p.get("in_per_mtok", 0.0)),
                    "out_per_mtok": float(p.get("out_per_mtok", 0.0))}
    except Exception:
        pass
    return {"in_per_mtok": 0.0, "out_per_mtok": 0.0}
