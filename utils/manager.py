import csv
import os
from dataclasses import asdict, fields
from typing import List, Type
import getpass

from datetime import datetime
from .secure_backup import restore_data, backup_data
from .models import Agencia, Colaborador, EstoqueItem, Kit, Usuario

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")


# ---------------- DE PARA ARQUIVOS ---------------- #

MODEL_FILE_MAP = {
    Agencia: "agencias.csv",
    Kit: "kits_cadastrados.csv",
    EstoqueItem: "estoque.csv",
    Usuario: "usuarios.csv",
    Colaborador: "colaboradores.csv",
}


# ---------------- PREFIXOS DE ID ---------------- #

MODEL_ID_PREFIX = {
    Agencia: "A",
    Colaborador: "C",
    EstoqueItem: "E",
    Kit: "K",
    Usuario: "U",
}


# ---------------- AUXILIARES ---------------- #

def read_csv(model):
    restore_data()
    file = os.path.join(DATA_DIR, MODEL_FILE_MAP[model])
    rows = []
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
    backup_data()
    return rows


def write_csv(model, data):
    restore_data()
    file = os.path.join(DATA_DIR, MODEL_FILE_MAP[model])
    with open(file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[f.name for f in fields(model)])
        writer.writeheader()
        writer.writerows(data)
    backup_data()


def dicts_to_objects(data: List[dict], modelo: Type):
    allowed = {f.name for f in fields(modelo)}
    objs = []
    for d in data:
        payload = {k: (v if v != "" else None) for k, v in d.items() if k in allowed}
        objs.append(modelo(**payload))
    return objs


def objects_to_dicts(objs: List):
    dicts = []
    for o in objs:
        d = asdict(o)
        if "qntd" in d and d["qntd"] is not None:
            d["qntd"] = str(d["qntd"])
        dicts.append(d)
    return dicts


def get_file_for_model(modelo: Type) -> str:
    return MODEL_FILE_MAP[modelo]


def gerar_id(modelo: Type) -> str:
    dados = read_csv(modelo)
    chave_id = [f.name for f in fields(modelo) if f.name.startswith("id_")][0]
    prefixo = MODEL_ID_PREFIX[modelo]
    existentes = []
    for d in dados:
        valor = d.get(chave_id, "")
        if valor.startswith(prefixo):
            try:
                existentes.append(int(valor[len(prefixo):]))
            except ValueError:
                continue

    proximo = max(existentes, default=0) + 1
    return f"{prefixo}{proximo:03d}"


def validar_relacionamentos(novo_registro, modelo):
    if modelo.__name__ == "Colaborador":
        usuarios = read_csv(Usuario)
        if not any(u["id_usuario"] == novo_registro.id_gestor for u in usuarios):
            raise ValueError(f"Gestor {novo_registro.id_gestor} não existe em usuários")
        kits = read_csv(Kit)
        if not any(k["id_kit"] == novo_registro.id_kit for k in kits):
            raise ValueError(f"Kit {novo_registro.id_kit} não existe em kits")
        agencias = read_csv(Agencia)
        if not any(a["id_agencia"] == novo_registro.id_agencia for a in agencias):
            raise ValueError(f"Agência {novo_registro.id_agencia} não existe em agencias")
    elif modelo.__name__ == "EstoqueItem":
        kits = read_csv(Kit)
        if not any(k["id_kit"] == novo_registro.id_kit for k in kits):
            raise ValueError(f"Kit {novo_registro.id_kit} não existe em kits")


# ---------------- DEBUG ---------------- #

def debug_dados(mostrar_tudo: bool = False, limite: int = 5):
    restore_data()
    print("\n=== DEBUG: Conteúdo dos arquivos CSV ===\n")
    for modelo, nome_arquivo in MODEL_FILE_MAP.items():
        caminho = os.path.join(DATA_DIR, nome_arquivo)
        if not os.path.exists(caminho):
            print(f"[AVISO] {nome_arquivo} não encontrado.")
            continue
        print(f"\n--- {nome_arquivo} ({modelo.__name__}) ---")
        with open(caminho, "r", encoding="utf-8-sig") as f:
            reader = list(csv.DictReader(f))
            if not reader:
                print("(vazio)")
            else:
                registros = reader if mostrar_tudo else reader[:limite]
                for i, row in enumerate(registros, start=1):
                    print(f"{i}: {row}")
                if not mostrar_tudo and len(reader) > limite:
                    print(f"... ({len(reader)-limite} registros ocultos)")
    print("\n=== FIM DEBUG ===\n")


# ---------------- LOG ---------------- #

def log_action(usuario: str, resultado: dict):
    restore_data()
    log_file = os.path.join(DATA_DIR, "logs.csv")
    file_exists = os.path.exists(log_file)
    fieldnames = [
        "usuario",
        "data",
        "hora",
        "acao",
        "linha_antes",
        "linha_depois",
    ]
    now = datetime.now()
    row = {
        "usuario": usuario or getpass.getuser(),
        "data": now.strftime("%Y-%m-%d"),
        "hora": now.strftime("%H:%M:%S"),
        "acao": resultado.get("acao", ""),
        "linha_antes": str(resultado.get("linha_antes") or ""),
        "linha_depois": str(resultado.get("linha_depois") or ""),
    }
    with open(log_file, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists or os.stat(log_file).st_size == 0:
            writer.writeheader()
        writer.writerow(row)
    backup_data()


# ---------------- ESTOQUE ---------------- #

def alterar_estoque(id_kit: str, item_nome: str, tamanho: str, quantidade: int):
    dados = read_csv(EstoqueItem)
    for item in dados:
        if (
            item["id_kit"] == id_kit
            and item["item"].lower() == item_nome.lower()
            and (not "camisa" in item_nome.lower() or item["tamanho_camisa"].upper() == tamanho.upper())
        ):
            qntd = int(item["qntd"])
            novo_qntd = qntd + quantidade
            if novo_qntd < 0:
                raise ValueError(f"Estoque insuficiente para {item_nome} ({tamanho})")
            item["qntd"] = str(novo_qntd)
            break
    write_csv(EstoqueItem, dados)


def ajustar_estoque_para_kit(id_kit: str, tamanho_camisa: str, delta: int):
    itens_kit = [row for row in read_csv(Kit) if row["id_kit"] == id_kit]
    dados_estoque = read_csv(EstoqueItem)
    selecionados = []
    for k in itens_kit:
        nome_item = (k.get("item") or "").lower()
        tam_kit = (k.get("tamanho_camisa") or "").upper()
        if "camisa" in nome_item:
            if tamanho_camisa and tam_kit == (tamanho_camisa or "").upper():
                selecionados.append(k)
        else:
            selecionados.append(k)
    for k in selecionados:
        nome_item = (k.get("item") or "")
        tam_kit = (k.get("tamanho_camisa") or "").upper()
        req = int(k.get("qntd") or 0)
        alvo = None
        for e in dados_estoque:
            mesmo_kit = e.get("id_kit") == id_kit
            mesmo_item = (e.get("item") or "").lower() == nome_item.lower()
            if "camisa" in nome_item.lower():
                mesmo_tam = (e.get("tamanho_camisa") or "").upper() == tam_kit
            else:
                mesmo_tam = True
            if mesmo_kit and mesmo_item and mesmo_tam:
                alvo = e
                break
        if not alvo:
            raise ValueError(f"Item '{nome_item}' (tam {tam_kit or 'NA'}) não encontrado no estoque para o kit {id_kit}")
        atual = int(alvo.get("qntd") or 0)
        novo = atual + delta * req
        if novo < 0:
            raise ValueError(f"Estoque insuficiente para item '{nome_item}' (tam {tam_kit or 'NA'})")
    for k in selecionados:
        nome_item = (k.get("item") or "")
        tam_kit = (k.get("tamanho_camisa") or "").upper()
        req = int(k.get("qntd") or 0)
        for e in dados_estoque:
            mesmo_kit = e.get("id_kit") == id_kit
            mesmo_item = (e.get("item") or "").lower() == nome_item.lower()
            if "camisa" in nome_item.lower():
                mesmo_tam = (e.get("tamanho_camisa") or "").upper() == tam_kit
            else:
                mesmo_tam = True
            if mesmo_kit and mesmo_item and mesmo_tam:
                atual = int(e.get("qntd") or 0)
                e["qntd"] = str(atual + delta * req)
                break
    write_csv(EstoqueItem, dados_estoque)


def validar_estoque_para_kit(id_kit: str, tamanho_camisa: str) -> bool:
    itens_kit = [row for row in read_csv(Kit) if row["id_kit"] == id_kit]
    dados_estoque = read_csv(EstoqueItem)
    checagens = []
    for k in itens_kit:
        nome_item = (k.get("item") or "")
        tam_kit = (k.get("tamanho_camisa") or "").upper()
        req = int(k.get("qntd") or 0)
        if req <= 0:
            continue
        if "camisa" in nome_item.lower():
            if tamanho_camisa and tam_kit == (tamanho_camisa or "").upper():
                checagens.append((nome_item, tam_kit, req))
        else:
            checagens.append((nome_item, None, req))
    for (nome_item, tam, req) in checagens:
        alvo = None
        for e in dados_estoque:
            if e.get("id_kit") != id_kit:
                continue
            if (e.get("item") or "").lower() != nome_item.lower():
                continue
            if tam:
                if (e.get("tamanho_camisa") or "").upper() != tam:
                    continue
            alvo = e
            break
        if not alvo:
            return False
        disponivel = int(alvo.get("qntd") or 0)
        if disponivel < req:
            return False
    return True


# ---------------- CRUD ---------------- #

def verificar_campos(modelo: Type, dados: dict) -> bool:
    modelo_fields = [f.name for f in fields(modelo)]
    preenchidos = [k for k, v in dados.items() if v not in (None, "")]
    return len(preenchidos) <= len(modelo_fields)


def listar_registros(modelo: Type) -> List:
    return dicts_to_objects(read_csv(modelo), modelo)


def adicionar_registro(novo_registro, modelo: Type):
    dados = read_csv(modelo)
    chave_id = [f.name for f in fields(modelo) if f.name.startswith("id_")][0]
    setattr(novo_registro, chave_id, gerar_id(modelo))
    validar_relacionamentos(novo_registro, modelo)
    if modelo == Colaborador:
        usuarios = read_csv(Usuario)
        gestor = next((u for u in usuarios if u["id_usuario"] == novo_registro.id_gestor), None)
        if gestor:
            novo_registro.nome_gestor = gestor["nome"]
            novo_registro.email_gestor = gestor["email"]
        kits = read_csv(Kit)
        kit = next((k for k in kits if k["id_kit"] == novo_registro.id_kit), None)
        if kit:
            novo_registro.nome_kit = kit["nome_kit"]
        agencias = read_csv(Agencia)
        agencia = next((a for a in agencias if a["id_agencia"] == novo_registro.id_agencia), None)
        if agencia:
            novo_registro.cidade_envio = agencia["cidade_envio"]
            novo_registro.uf_envio = agencia["uf_envio"]
        id_kit = novo_registro.id_kit
        tamanho_camisa = novo_registro.tamanho_camisa
        if not validar_estoque_para_kit(id_kit, tamanho_camisa):
            raise ValueError(f"Estoque insuficiente para kit {id_kit} (camisa {tamanho_camisa})")
        ajustar_estoque_para_kit(id_kit, tamanho_camisa, delta=-1)

    linha_depois = asdict(novo_registro)
    dados.append(linha_depois)
    write_csv(modelo, dados)

    return {
        'acao': "REGISTRAR",
        'linha_antes': None,
        'linha_depois': linha_depois
    }


def atualizar_registro(chave, valor_chave, novos_dados, modelo: Type):
    dados = read_csv(modelo)
    linha_antes, linha_depois = None, None
    for d in dados:
        if d.get(chave) == valor_chave:
            linha_antes = d.copy()
            if modelo == Colaborador:
                id_kit_antigo = d["id_kit"]
                tamanho_antigo = d.get("tamanho_camisa", "")
                id_kit_novo = novos_dados.get("id_kit", id_kit_antigo)
                tamanho_novo = novos_dados.get("tamanho_camisa", tamanho_antigo)

                if id_kit_novo != id_kit_antigo or tamanho_novo != tamanho_antigo:
                    ajustar_estoque_para_kit(id_kit_antigo, tamanho_antigo, delta=+1)
                    if not validar_estoque_para_kit(id_kit_novo, tamanho_novo):
                        raise ValueError(f"Estoque insuficiente para kit {id_kit_novo} (camisa {tamanho_novo})")
                    ajustar_estoque_para_kit(id_kit_novo, tamanho_novo, delta=-1)
            d.update({k: v for k, v in novos_dados.items() if v is not None})
            linha_depois = d.copy()
            break
    write_csv(modelo, dados)
    return {
        'acao': "ATUALIZAR",
        'linha_antes': linha_antes,
        'linha_depois': linha_depois
    }


def remover_registro(chave, valor_chave, modelo: Type):
    dados = read_csv(modelo)
    novos_dados = []
    linha_antes = None
    for d in dados:
        if d.get(chave) == valor_chave:
            linha_antes = d.copy()
            if modelo == Colaborador:
                id_kit = d["id_kit"]
                tamanho_camisa = d.get("tamanho_camisa", "")
                ajustar_estoque_para_kit(id_kit, tamanho_camisa, delta=+1)
            continue 
        novos_dados.append(d)
    write_csv(modelo, novos_dados)
    return {
        'acao': "REMOVER",
        'linha_antes': linha_antes,
        'linha_depois': None
    }