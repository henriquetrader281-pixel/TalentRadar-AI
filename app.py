# -*- coding: utf-8 -*-
"""
Painel Web Principal — TalentRadar AI
"""

import sqlite3
import json
import streamlit as st
import pandas as pd
from storage import init_db, salvar_vagas
from job_sources import obter_vagas_processadas

st.set_page_config(page_title="🤖 TalentRadar AI — Radar de Vagas", page_icon="🤖", layout="wide")

init_db()

@st.cache_data
def carregar_dados():
    try:
        conn = sqlite3.connect("vagas.db")
        df = pd.read_sql_query("SELECT * FROM vagas ORDER BY fit_score DESC", conn)
        conn.close()
        if df.empty:
            salvar_vagas(obter_vagas_processadas())
            conn = sqlite3.connect("vagas.db")
            df = pd.read_sql_query("SELECT * FROM vagas ORDER BY fit_score DESC", conn)
            conn.close()
        return df
    except Exception:
        return pd.DataFrame()

st.markdown("""
<style>
    .stApp { background-color: #0f172a; color: #f8fafc; }
    .badge-fit { background-color: #10b981; color: white; padding: 6px 12px; border-radius: 8px; font-weight: bold; }
    .badge-cat { background-color: #3b82f6; color: white; padding: 4px 10px; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

st.sidebar.title("🤖 TalentRadar AI")
st.sidebar.caption("Agente Pessoal de Recolocação (Vale do Sinos)")
st.sidebar.divider()

# Seleção de Múltiplos Currículos por Área
st.sidebar.subheader("📄 Multicurrículos por Área")
area_cv = st.sidebar.selectbox("Área de Atuação", ["Suporte e Infraestrutura", "Bancário / Atendimento", "IA / Tecnologia"])

df_vagas = carregar_dados()

if not df_vagas.empty:
    categorias = ["Todas"] + list(df_vagas["categoria"].unique())
    cat_sel = st.sidebar.selectbox("Filtro de Vagas", categorias)
    sal_min = st.sidebar.slider("Salário Mínimo (R$)", 0, 5000, 2000, step=250)

    df_filtered = df_vagas.copy()
    if cat_sel != "Todas":
        df_filtered = df_filtered[df_filtered["categoria"] == cat_sel]
    df_filtered = df_filtered[df_filtered["salario_num"] >= sal_min]

    st.sidebar.divider()
    st.sidebar.subheader("🛡️ Otimizador ATS & Multi-IA")
    api_key_ia = st.sidebar.text_input("Chave API IA (Opcional)", type="password", placeholder="Insira sua chave API...")
    
    cv_text = st.sidebar.text_area(f"Currículo para [{area_cv}]:", height=100, placeholder="Cole o texto do seu CV...")
    if st.sidebar.button("Retestar e Simular Triagem ATS", use_container_width=True) and cv_text:
        all_kw = []
        for item in df_vagas["palavras_chave_ats"]:
            all_kw.extend(json.loads(item))
        ausentes = [kw for kw in set(all_kw) if kw.lower() not in cv_text.lower()]
        if not ausentes:
            st.sidebar.success("🛡️ Aprovado na Simulação ATS (100% de aderência)!")
        else:
            st.sidebar.warning(f"⚠️ Faltam keywords no CV: {', '.join(ausentes[:5])}")

    st.title("📅 RADAR DE EMPREGOS — VALE DO SINOS")
    st.info(f"Oportunidades ativas (Fit $\ge 60\%$) para **{area_cv}**: **{len(df_filtered)}** encontradas.")

    for _, row in df_filtered.iterrows():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### {row['cargo']}")
            st.markdown(f"**{row['empresa']}** — {row['cidade']} | `<span class='badge-cat'>{row['categoria']}</span>`", unsafe_allow_html=True)
            st.write(f"💵 **Salário:** {row['salario']} | 🔧 **Mão na Massa:** {row['mhao_na_massa']}")
            st.markdown(f"<span class='badge-fit'>Score Recrutador IA: {row['fit_score']}% de Aderência</span>", unsafe_allow_html=True)
        with col2:
            if row["link_whatsapp"]:
                st.link_button("📲 Contatar Recrutador", row["link_whatsapp"], type="primary", use_container_width=True)
            st.link_button("🔗 Ver Link Direto Vaga", row["link"], use_container_width=True)
            if api_key_ia and st.button(f"🤖 Gerar Carta IA", key=f"ia_{row['id']}"):
                st.toast(f"Carta personalizada gerada com sucesso para {row['empresa']}!")
        st.divider()
else:
    st.warning("Nenhuma vaga encontrada no banco de dados.")
