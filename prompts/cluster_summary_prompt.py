import json

def build_cluster_summary_prompt(brand: str, clusters_payload: list) -> str:
    """
    Builds a strict JSON-only prompt for local LLaMA.
    """

    instruction = (
        "You MUST output VALID JSON ONLY.\n"
        "No explanations. No markdown. No extra text.\n\n"
        "You summarize customer feedback clusters.\n"
        "Rules:\n"
        "- Base conclusions ONLY on the provided review examples.\n"
        "- Do NOT speculate about causes.\n"
        "- Do NOT suggest solutions.\n"
        "- Keep language neutral and factual.\n"
        "- Each cluster is independent.\n\n"
        "For each cluster, return:\n"
        "- cluster_id (int)\n"
        "- summary (1–2 sentences)\n"
        "- primary_issue (2–4 words)\n"
        "- user_impact: one of low | medium | high\n\n"
        "Return JSON in this exact structure:\n"
        "{\n"
        '  "brand": "<brand>",\n'
        '  "cluster_summaries": [\n'
        "    {\n"
        '      "cluster_id": 1,\n'
        '      "summary": "...",\n'
        '      "primary_issue": "...",\n'
        '      "user_impact": "low"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
    )

    payload = {
        "brand": brand,
        "clusters": clusters_payload
    }

    return instruction + "Input:\n" + json.dumps(payload, ensure_ascii=False)
