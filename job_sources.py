# -*- coding: utf-8 -*-
"""
Módulo de Fontes de Vagas e Cálculo de Aderência (Fit 60% a 100%)
"""

import re
import urllib.parse
from datetime import datetime

PERFIL_CANDIDATO = {
    "skills": [
        "suporte tecnico", "suporte ao usuario", "suporte", "manutencao de computadores",
        "hardware", "windows", "redes", "infraestrutura", "cabeamento",
        "roteadores", "switches", "crimpagem", "cftv", "atendimento", "comunicacao"
    ]
}

BANCO_VAGAS_INICIAL = [
    {
        "empresa": "Sicredi Caminho das Águas",
        "cargo": "Assistente de Atendimento e Negócios",
        "cidade": "Novo Hamburgo",
        "salario": "R$ 2.900,00",
        "requisitos": ["atendimento", "suporte ao usuario", "comunicacao", "vendas"],
        "mhao_na_massa": "Não",
        "link": "https://www.sicredi.com.br/site/sobre-nos/carreiras/",
        "whatsapp": "5551999990001",
        "categoria": "Bancária",
        "palavras_chave_ats": ["atendimento ao cliente", "resolucao de problemas", "comunicacao", "metas", "suporte"]
    },
    {
        "empresa": "Tech Sinos AI",
        "cargo": "Auxiliar de Treinamento de Modelos de IA",
        "cidade": "Novo Hamburgo",
        "salario": "R$ 3.000,00",
        "requisitos": ["suporte", "windows", "inteligencia artificial", "tecnologia"],
        "mhao_na_massa": "Sim",
        "link": "https://www.infojobs.com.br/",
        "whatsapp": "5551999990002",
        "categoria": "Inteligência Artificial",
        "palavras_chave_ats": ["inteligencia artificial", "ia", "machine learning", "tecnologia", "curadoria de dados", "suporte"]
    },
    {
        "empresa": "Infratech NH",
        "cargo": "Técnico Auxiliar de Redes e Infra",
        "cidade": "Novo Hamburgo",
        "salario": "R$ 2.900,00",
        "requisitos": ["redes", "cabeamento", "infraestrutura", "suporte"],
        "mhao_na_massa": "Sim",
        "link": "https://www.infojobs.com.br/",
        "whatsapp": "5551966666666",
        "categoria": "TI / Suporte",
        "palavras_chave_ats": ["redes", "infraestrutura", "cabeamento", "suporte tecnico", "hardware", "troubleshooting"]
    },
    {
        "empresa": "Wine Tecnologia",
        "cargo": "Técnico de TI (Projetos / Rollout)",
        "cidade": "Novo Hamburgo",
        "salario": "R$ 2.073,38 a R$ 3.226,01",
        "requisitos": ["suporte tecnico", "hardware", "infraestrutura", "rollout", "escala"],
        "mhao_na_massa": "Sim",
        "link": "https://www.trabalhabrasil.com.br/vagas-de-emprego-em-novo-hamburgo-rs/tecnico-de-ti/7448707",
        "whatsapp": "5551999999999",
        "categoria": "TI / Suporte",
        "palavras_chave_ats": ["suporte tecnico", "hardware", "infraestrutura", "rollout", "escala"]
    }
]

def extrair_maior_salario(valor_salario: str) -> float:
    numeros = re.findall(r'\d+\.?\d*', valor_salario.replace('.', '').replace(',', '.'))
    if not numeros:
        return 0.0
    return max([float(n) for n in numeros])

def calcular_fit(requisitos: list) -> int:
    skills_candidato = set(PERFIL_CANDIDATO["skills"])
    skills_vaga = set(requisitos)
    if not skills_vaga:
        return 60
    match = skills_vaga.intersection(skills_candidato)
    score = int((len(match) / len(skills_vaga)) * 100)
    return max(score, 60) if len(match) > 0 else score

def obter_vagas_processadas(fit_minimo=60):
    vagas_finais = []
    data_hoje = datetime.now().strftime("%Y-%m-%d")
    
    for v in BANCO_VAGAS_INICIAL:
        fit = calcular_fit(v["requisitos"])
        if fit >= fit_minimo:
            v["fit_score"] = fit
            v["salario_num"] = extrair_maior_salario(v["salario"])
            v["data_coleta"] = data_hoje
            
            if v.get("whatsapp"):
                msg = f"Olá! Vi a vaga de {v['cargo']} na {v['empresa']} ({v['cidade']}). Tenho forte aderência ao perfil."
                v["link_whatsapp"] = f"https://api.whatsapp.com/send?phone={v['whatsapp']}&text={urllib.parse.quote(msg)}"
            else:
                v["link_whatsapp"] = ""
                
            vagas_finais.append(v)
            
    return vagas_finais
