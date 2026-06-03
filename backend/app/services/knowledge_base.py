"""Knowledge base service — CRUD and semantic search against LLM."""

import json
import re
from typing import Optional
from .db import get_db
from ..config import get_settings


def list_entries(category: Optional[str] = None, search: Optional[str] = None) -> list[dict]:
    """List knowledge base entries, optionally filtered."""
    db = get_db()
    params = []
    sql = "SELECT * FROM knowledge_base WHERE 1=1"

    if category:
        sql += " AND category = ?"
        params.append(category)
    if search:
        sql += " AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like])

    sql += " ORDER BY risk_level DESC, id ASC"
    rows = db.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_entry(entry_id: int) -> Optional[dict]:
    db = get_db()
    r = db.execute("SELECT * FROM knowledge_base WHERE id = ?", (entry_id,)).fetchone()
    return dict(r) if r else None


def create_entry(title: str, category: str, content: str, risk_level: str = "中", tags: str = "") -> dict:
    db = get_db()
    cur = db.execute(
        "INSERT INTO knowledge_base (title, category, content, risk_level, tags) VALUES (?, ?, ?, ?, ?)",
        (title, category, content, risk_level, tags),
    )
    db.commit()
    return get_entry(cur.lastrowid)


def update_entry(entry_id: int, **kwargs) -> Optional[dict]:
    db = get_db()
    fields = {k: v for k, v in kwargs.items() if v is not None}
    if not fields:
        return get_entry(entry_id)
    fields["updated_at"] = "datetime('now', 'localtime')"
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    # Handle special case: updated_at is SQL expression
    set_clause = set_clause.replace("updated_at = ?", "updated_at = datetime('now', 'localtime')")
    vals = [v for k, v in fields.items() if k != "updated_at"]
    vals.append(entry_id)
    db.execute(f"UPDATE knowledge_base SET {set_clause} WHERE id = ?", vals)
    db.commit()
    return get_entry(entry_id)


def delete_entry(entry_id: int) -> bool:
    db = get_db()
    db.execute("DELETE FROM knowledge_base WHERE id = ?", (entry_id,))
    db.commit()
    return db.total_changes > 0


def list_categories() -> list[str]:
    db = get_db()
    rows = db.execute("SELECT DISTINCT category FROM knowledge_base ORDER BY category").fetchall()
    return [r["category"] for r in rows]


# ── LLM-augmented matching ──

def semantic_search(query: str, top_k: int = 5) -> list[dict]:
    """
    Search knowledge base by semantic relevance using LLM.
    Returns top_k matching entries with relevance scores.
    """
    db = get_db()
    all_entries = db.execute("SELECT * FROM knowledge_base ORDER BY id").fetchall()
    if not all_entries:
        return []

    settings = get_settings()
    if not settings.llm_api_key:
        # Fallback: keyword matching
        return keyword_search(query, top_k)

    # Use LLM to rank relevance
    kb_text = "\n\n".join([
        f"[{e['id']}] {e['title']}（{e['category']}）\n{e['content'][:200]}"
        for e in all_entries
    ])

    prompt = f"""你是一个合同审核专家。用户正在审核一份合同，需要找出知识库中最相关的标准条款。

用户查询/合同文本：
{query[:1000]}

知识库条目：
{kb_text}

请判断哪些知识库条目与查询最相关。返回 JSON 数组，每个元素包含 id 和 relevance（0-100的整数分数）：
[{{"id": 1, "relevance": 85}}, ...]

只返回最相关的前{top_k}条（relevance >= 30）。如果都不相关，返回空数组 []。
只输出 JSON，不要额外文字。"""

    try:
        import httpx
        resp = httpx.post(
            f"{settings.llm_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"},
            json={
                "model": settings.llm_model,
                "messages": [{"role": "system", "content": "你是合同审核专家，擅长匹配合同条款与标准条款。"},
                             {"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 1024,
            },
            timeout=30,
        )
        result = resp.json()
        content = result["choices"][0]["message"]["content"]

        # Parse JSON from response
        json_match = re.search(r"\[.*?\]", content, re.DOTALL)
        if json_match:
            matches = json.loads(json_match.group())
            # Enrich with full entry data
            entry_map = {e["id"]: dict(e) for e in all_entries}
            enriched = []
            for m in sorted(matches, key=lambda x: x["relevance"], reverse=True)[:top_k]:
                entry = entry_map.get(m["id"])
                if entry:
                    entry["relevance"] = m["relevance"]
                    enriched.append(entry)
            return enriched
    except Exception:
        pass

    return keyword_search(query, top_k)


def keyword_search(query: str, top_k: int = 5) -> list[dict]:
    """Simple keyword fallback search."""
    db = get_db()
    words = [w for w in re.split(r"[，。、；：\s,.;: ]", query) if len(w) >= 2]
    if not words:
        return []

    like_clauses = " OR ".join(["(title LIKE ? OR content LIKE ? OR tags LIKE ?)" for _ in words])
    params = []
    for w in words:
        like = f"%{w}%"
        params.extend([like, like, like])

    rows = db.execute(
        f"SELECT *, (CASE WHEN {' + '.join(['1'] * len(words))} END) as relevance "
        f"FROM knowledge_base WHERE {like_clauses} "
        f"ORDER BY risk_level DESC, id ASC LIMIT ?",
        params + [top_k],
    ).fetchall()
    return [dict(r) for r in rows]
