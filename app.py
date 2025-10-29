# streamlit_app_bling.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import io
import time
import requests
import json
# ---------- Autenticação Simples ----------
def login():
    st.title("🔐 Acesso Restrito")
    usuario = st.text_input("Usuário", placeholder="Digite seu usuário")
    senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")
    if st.button("Entrar"):
        if usuario == "admin" and senha == "rigarr1234":  # 🔴 Troque para sua senha segura
            st.session_state["autenticado"] = True
            st.success("✅ Login realizado com sucesso!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ Usuário ou senha incorretos")

# Verifica autenticação antes de mostrar qualquer coisa
if "autenticado" not in st.session_state or not st.session_state["autenticado"]:
    login()
    st.stop()

# ---------- Configurações Bling ----------
CLIENT_ID = "518cdebe485bb9e24f0d7e717e45614f8ae856d8"
CLIENT_SECRET = "6092684fda7d8df500cd2f47b2921f1f13f22e0229f74fe8995f556681fc"
TOKEN_URL = "https://bling.com.br/Api/v3/oauth/token"
TOKEN_FILE = r'C:\Users\LeonardoCampos\HBox\MEU DRIVE\BEES\Bling\bling_token.json'
NFE_API_URL = "https://api.bling.com.br/Api/v3/nfe"

# ---------- Funções de Token ----------
def carregar_token():
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        st.warning(f"⚠️ Problema ao carregar '{TOKEN_FILE}'.")
        return None

def salvar_token(token_data):
    token_data["obtido_em"] = datetime.now().isoformat()
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(token_data, f, indent=4)

def token_expirado(token_data):
    if not token_data or "access_token" not in token_data:
        return True
    buffer_segundos = 300
    obtido_em = datetime.fromisoformat(token_data["obtido_em"])
    expira_em = obtido_em + timedelta(seconds=token_data.get("expires_in", 0) - buffer_segundos)
    return datetime.now() >= expira_em

def renovar_token(token_data):
    st.info("🔄 Renovando token...")
    data = {"grant_type": "refresh_token", "refresh_token": token_data["refresh_token"]}
    auth = (CLIENT_ID, CLIENT_SECRET)
    try:
        response = requests.post(TOKEN_URL, data=data, auth=auth)
        response.raise_for_status()
        novo_token = response.json()
        salvar_token(novo_token)
        st.success("✅ Token renovado com sucesso!")
        return novo_token
    except Exception as e:
        st.error(f"❌ Falha ao renovar token: {e}")
        return None

def obter_token_valido():
    token_data = carregar_token()
    if token_data is None:
        st.error(f"Token inicial não encontrado em '{TOKEN_FILE}'.")
        return None
    if token_expirado(token_data):
        token_data = renovar_token(token_data)
    return token_data["access_token"] if token_data else None

# ---------- Funções de notas ----------
def parse_data_emissao(data_str):
    """
    Converte string de data no formato brasileiro 'dd/mm/yyyy' em datetime.date
    """
    try:
        return datetime.strptime(data_str, "%d/%m/%Y").date()
    except ValueError:
        raise ValueError(f"Formato de data inválido: {data_str}. Use dd/mm/yyyy")

def get_single_invoice_details(nfe_id, access_token, max_retries=5):
    url = f"{NFE_API_URL}/{nfe_id}"
    headers = {'Accept': 'application/json', 'Authorization': f'Bearer {access_token}'}
    retries = 0
    retry_delay = 1
    while retries <= max_retries:
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get('data', None)
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                time.sleep(retry_delay)
                retry_delay *= 2
                retries += 1
            else:
                return None
        except:
            return None
    return None

def process_invoice_to_rows(invoice):
    contato = invoice.get('contato', {}) or {}
    contato_data = {
        'contato_id': contato.get('id'),
        'contato_nome': contato.get('nome'),
        'contato_numeroDocumento': contato.get('numeroDocumento'),
        'contato_ie': contato.get('inscricaoEstadual'),
        'contato_email': contato.get('email'),
        'contato_telefone': contato.get('telefone')
    }

    cabecalho = {
        'id_nfe': invoice.get('id'),
        'numero_nfe': invoice.get('numero'),
        'serie_nfe': invoice.get('serie'),
        'dataEmissao_nfe': invoice.get('dataEmissao'),
        'dataEntrada_nfe': invoice.get('dataEntradaSaida'),
        'valor_total_nfe': invoice.get('valorTotal'),
        'valor_frete_nfe': invoice.get('valorFrete'),
        'valor_seguro_nfe': invoice.get('valorSeguro'),
        'valor_desconto_nfe': invoice.get('valorDesconto'),
        'pesoBruto_nfe': invoice.get('pesoBruto'),
        'pesoLiquido_nfe': invoice.get('pesoLiquido'),
        'observacoes_nfe': invoice.get('observacoes') or ""
    }

    rows = []
    itens = invoice.get('itens', []) or []

    if itens:
        for item in itens:
            row = {
                **cabecalho,
                **contato_data,
                'item_id': item.get('id'),
                'item_codigo': item.get('codigo'),
                'item_descricao': item.get('descricao'),
                'item_unidade': item.get('unidade'),
                'item_quantidade': item.get('quantidade'),
                'item_valorUnidade': item.get('valorUnidade'),
                'item_valorTotal': item.get('valorTotal')
            }
            impostos = item.get('impostos', {}) or {}
            icms = impostos.get('icms', {}) or {}
            ipi = impostos.get('ipi', {}) or {}
            pis = impostos.get('pis', {}) or {}
            cofins = impostos.get('cofins', {}) or {}
            row.update({
                'icms_valor': icms.get('valor'),
                'ipi_valor': ipi.get('valor'),
                'pis_valor': pis.get('valor'),
                'cofins_valor': cofins.get('valor')
            })
            rows.append(row)
    else:
        row = {**cabecalho, **contato_data,
               'item_id': None, 'item_codigo': None, 'item_descricao': None,
               'item_unidade': None, 'item_quantidade': None,
               'item_valorUnidade': None, 'item_valorTotal': None}
        rows.append(row)
    return rows

def buscar_notas_df(access_token, data_inicio, data_fim, tipo_nota):
    page = 1
    all_rows = []
    headers = {'Accept': 'application/json', 'Authorization': f'Bearer {access_token}'}
    while True:
        params = {
            'pagina': page,
            'ordem': 'desc',
            'ordenarPor': 'dataEmissao',
            'tipo': tipo_nota
        }
        response = requests.get(NFE_API_URL, headers=headers, params=params)
        if response.status_code != 200:
            break
        nfes = response.json().get("data", [])
        if not nfes:
            break
        for nfe in nfes:
            # converte data Emissão da API para objeto date
            data_emissao_str = nfe.get("dataEmissao")
        try:
            data_emissao = datetime.strptime(data_emissao_str, "%Y-%m-%d %H:%M:%S").date()
        except ValueError:
            data_emissao = datetime.strptime(data_emissao_str, "%Y-%m-%d").date()

            if not (data_inicio <= data_emissao <= data_fim):
                continue
            detailed_invoice = get_single_invoice_details(str(nfe.get("id")), access_token)
            if detailed_invoice:
                rows = process_invoice_to_rows(detailed_invoice)
                all_rows.extend(rows)
        if len(nfes) < 100:
            break
        page += 1

    df = pd.DataFrame(all_rows)
    # Formata colunas de data para dd/mm/yyyy
    for col in df.columns:
        if "data" in col.lower():
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%d/%m/%Y')
    return df

# ---------- Streamlit ----------
st.set_page_config(page_title="Notas Fiscais Bling", layout="wide")
st.title("📄 Download de Notas Fiscais - Bling")
st.markdown("Por Leonardo Campos")
st.markdown("Selecione o período e o tipo de nota para baixar em CSV.")

tipo_nota = st.selectbox("Tipo de Nota", ["E", "S"], format_func=lambda x: "Entrada" if x=="E" else "Saída")
data_inicio = st.date_input("Data Inicial", date.today() - timedelta(days=30))
st.write("Data selecionada:", data_inicio.strftime("%d/%m/%Y"))

data_fim = st.date_input("Data Final", date.today())
st.write("Data selecionada:", data_fim.strftime("%d/%m/%Y"))


if st.button("🔍 Buscar Notas Fiscais"):
    if data_inicio > data_fim:
        st.error("Data inicial não pode ser maior que a final!")
    else:
        token = obter_token_valido()
        if token:
            with st.spinner("Buscando notas... ⏳"):
                df = buscar_notas_df(token, data_inicio, data_fim, tipo_nota)
                if not df.empty:
                    st.dataframe(df)  # preview das notas
                    csv_buffer = io.StringIO()
                    df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
                    st.download_button(
                        label="⬇️ Baixar CSV",
                        data=csv_buffer.getvalue(),
                        file_name=f"notas_{tipo_nota}_{data_inicio.strftime('%d-%m-%Y')}_{data_fim.strftime('%d-%m-%Y')}.csv",
                        mime="text/csv"
                    )
