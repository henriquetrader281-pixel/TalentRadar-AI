from __future__ import annotations

import hmac
from contextlib import contextmanager
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.responses import FileResponse, JSONResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pydantic import BaseModel, Field, field_validator

BASE_DIR = Path(__file__).resolve().parent
COOKIE_NAME = "talentradar_session"
SESSION_MAX_AGE = 60 * 60 * 12

app = FastAPI(title="TalentRadar AI API", version="2.0.0")


def get_database_url() -> str:
    value = os.getenv("DATABASE_URL", "").strip()
    if not value:
        raise HTTPException(
            status_code=503,
            detail="Banco não configurado. Cadastre DATABASE_URL com uma conexão PostgreSQL persistente.",
        )
    return value


def get_serializer() -> URLSafeTimedSerializer:
    secret = os.getenv("SESSION_SECRET", "").strip()
    if len(secret) < 32:
        raise HTTPException(
            status_code=503,
            detail="Autenticação não configurada. Defina SESSION_SECRET com pelo menos 32 caracteres.",
        )
    return URLSafeTimedSerializer(secret, salt="talentradar-auth-v1")


@contextmanager
def db_connect():
    conn = psycopg.connect(get_database_url(), row_factory=dict_row, connect_timeout=8)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id BIGSERIAL PRIMARY KEY,
                    empresa TEXT NOT NULL,
                    cargo TEXT NOT NULL,
                    cidade TEXT NOT NULL DEFAULT '',
                    salario TEXT NOT NULL DEFAULT 'A combinar',
                    salario_num NUMERIC(12,2) NOT NULL DEFAULT 0,
                    fit_score INTEGER NOT NULL DEFAULT 0 CHECK (fit_score BETWEEN 0 AND 100),
                    categoria TEXT NOT NULL DEFAULT 'Outros',
                    mao_na_massa TEXT NOT NULL DEFAULT '',
                    link TEXT NOT NULL DEFAULT '',
                    link_whatsapp TEXT NOT NULL DEFAULT '',
                    palavras_chave_ats JSONB NOT NULL DEFAULT '[]'::jsonb,
                    observacoes TEXT NOT NULL DEFAULT '',
                    origem TEXT NOT NULL DEFAULT 'Manual',
                    data_coleta TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS jobs_fit_score_idx ON jobs (fit_score DESC)")
        conn.commit()
        yield conn
    finally:
        conn.close()


def require_auth(request: Request) -> dict[str, Any]:
    token = request.cookies.get(COOKIE_NAME, "")
    if not token:
        raise HTTPException(status_code=401, detail="Faça login para continuar.")
    try:
        data = get_serializer().loads(token, max_age=SESSION_MAX_AGE)
        if data.get("authenticated") is not True:
            raise HTTPException(status_code=401, detail="Sessão inválida.")
        return data
    except (BadSignature, SignatureExpired):
        raise HTTPException(status_code=401, detail="Sessão expirada. Entre novamente.")


class LoginInput(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class JobInput(BaseModel):
    empresa: str = Field(min_length=1, max_length=180)
    cargo: str = Field(min_length=1, max_length=180)
    cidade: str = Field(default="", max_length=120)
    salario: str = Field(default="A combinar", max_length=100)
    salario_num: float = Field(default=0, ge=0, le=10000000)
    fit_score: int = Field(default=0, ge=0, le=100)
    categoria: str = Field(default="Outros", max_length=100)
    mao_na_massa: str = Field(default="", max_length=120)
    link: str = Field(default="", max_length=2000)
    link_whatsapp: str = Field(default="", max_length=2000)
    palavras_chave_ats: list[str] = Field(default_factory=list, max_length=100)
    observacoes: str = Field(default="", max_length=5000)
    origem: str = Field(default="Manual", max_length=100)

    @field_validator("link", "link_whatsapp")
    @classmethod
    def validate_web_urls(cls, value: str) -> str:
        if value and not value.lower().startswith(("https://", "http://")):
            raise ValueError("Os links devem começar com http:// ou https://.")
        return value


@app.get("/")
def home():
    page = BASE_DIR / "public" / "index.html"
    if page.exists():
        return FileResponse(page)
    return JSONResponse({"service": "TalentRadar AI API", "docs": "/docs"})


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "TalentRadar AI",
        "environment": os.getenv("VERCEL_ENV", "unknown"),
        "deployment_url": os.getenv("VERCEL_URL", ""),
        "commit": os.getenv("VERCEL_GIT_COMMIT_SHA", "")[:12],
        "app_password_configured": bool(os.getenv("APP_PASSWORD", "")),
        "session_secret_configured": len(os.getenv("SESSION_SECRET", "").strip()) >= 32,
        "database_configured": bool(os.getenv("DATABASE_URL", "").strip()),
    }


@app.post("/api/login")
def login(payload: LoginInput, request: Request, response: Response):
    expected = os.getenv("APP_PASSWORD", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Defina APP_PASSWORD nas variáveis de ambiente da Vercel.")
    if len(os.getenv("SESSION_SECRET", "")) < 32:
        raise HTTPException(status_code=503, detail="Defina SESSION_SECRET com pelo menos 32 caracteres.")
    if not hmac.compare_digest(payload.password.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Senha incorreta.")
    token = get_serializer().dumps({"authenticated": True, "issued_at": datetime.now(timezone.utc).isoformat()})
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=request.url.scheme == "https" or os.getenv("VERCEL") == "1",
        samesite="strict",
        path="/",
    )
    return {"ok": True}


@app.post("/api/logout")
def logout(request: Request, response: Response):
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, secure=request.url.scheme == "https" or os.getenv("VERCEL") == "1", samesite="strict")
    return {"ok": True}


@app.get("/api/session")
def session(_: dict = Depends(require_auth)):
    return {"authenticated": True}


@app.get("/api/jobs")
def list_jobs(
    _: dict = Depends(require_auth),
    q: str = "",
    categoria: str = "",
    fit_min: int = 0,
    limit: int = 200,
):
    if not 0 <= fit_min <= 100:
        raise HTTPException(status_code=422, detail="fit_min deve estar entre 0 e 100.")
    limit = max(1, min(limit, 500))
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, empresa, cargo, cidade, salario, salario_num, fit_score,
                       categoria, mao_na_massa, link, link_whatsapp,
                       palavras_chave_ats, observacoes, origem, data_coleta, created_at
                FROM jobs
                WHERE fit_score >= %s
                  AND (%s = '' OR categoria = %s)
                  AND (%s = '' OR empresa ILIKE %s OR cargo ILIKE %s OR cidade ILIKE %s)
                ORDER BY fit_score DESC, data_coleta DESC
                LIMIT %s
                """,
                (fit_min, categoria, categoria, q, f"%{q}%", f"%{q}%", f"%{q}%", limit),
            )
            rows = cur.fetchall()
    for row in rows:
        for key in ("data_coleta", "created_at"):
            if row.get(key):
                row[key] = row[key].isoformat()
        if row.get("salario_num") is not None:
            row["salario_num"] = float(row["salario_num"])
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT categoria FROM jobs WHERE categoria <> '' ORDER BY categoria")
            categories = [item["categoria"] for item in cur.fetchall()]
    return {"items": rows, "count": len(rows), "categories": categories}


@app.post("/api/jobs", status_code=201)
def create_job(payload: JobInput, _: dict = Depends(require_auth)):
    values = payload.model_dump()
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO jobs
                    (empresa, cargo, cidade, salario, salario_num, fit_score, categoria,
                     mao_na_massa, link, link_whatsapp, palavras_chave_ats, observacoes, origem)
                VALUES (%(empresa)s, %(cargo)s, %(cidade)s, %(salario)s, %(salario_num)s,
                        %(fit_score)s, %(categoria)s, %(mao_na_massa)s, %(link)s, %(link_whatsapp)s,
                        %(palavras_chave_ats)s::jsonb, %(observacoes)s, %(origem)s)
                RETURNING id
                """,
                {**values, "palavras_chave_ats": json.dumps(values["palavras_chave_ats"])},
            )
            job_id = cur.fetchone()["id"]
        conn.commit()
    return {"ok": True, "id": job_id}


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: int, _: dict = Depends(require_auth)):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM jobs WHERE id = %s RETURNING id", (job_id,))
            deleted = cur.fetchone()
        conn.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail="Vaga não encontrada.")
    return {"ok": True, "id": job_id}
