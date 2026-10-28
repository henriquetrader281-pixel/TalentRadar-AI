# -*- coding: utf-8 -*-
"""
Módulo de Persistência SQLite — TalentRadar AI
Banco de dados leve para acompanhamento semanal e aprimoramento.
"""

import sqlite3
import json

DB_FILE = "vagas.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vagas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa TEXT,
            cargo TEXT,
            cidade TEXT,
            salario TEXT,
            salario_num REAL,
            fit_score INTEGER,
            mhao_na_massa TEXT,
            link TEXT,
            whatsapp TEXT,
            link_whatsapp TEXT,
            categoria TEXT,
            palavras_chave_ats TEXT,
            data_coleta TEXT
        )
    """)
    conn.commit()
    conn.close()

def salvar_vagas(lista_vagas):
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM vagas")
    
    for v in lista_vagas:
        cursor.execute("""
            INSERT INTO vagas (
                empresa, cargo, cidade, salario, salario_num, fit_score, 
                mhao_na_massa, link, whatsapp, link_whatsapp, categoria, 
                palavras_chave_ats, data_coleta
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            v["empresa"], v["cargo"], v["cidade"], v["salario"], v["salario_num"], v["fit_score"],
            v["mhao_na_massa"], v["link"], v.get("whatsapp", ""), v.get("link_whatsapp", ""),
            v["categoria"], json.dumps(v["palavras_chave_ats"]), v["data_coleta"]
        ))
    conn.commit()
    conn.close()
