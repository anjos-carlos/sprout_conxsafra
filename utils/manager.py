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
    return [asdict(o) for o in objs]


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
    dados = read_csv(EstoqueItem)
    for item in dados:
        if item["id_kit"] == id_kit:
            nome_item = item["item"].lower()
            tamanho_item = item.get("tamanho_camisa", "").upper()
            qntd = int(item["qntd"])
            if "camisa" in nome_item and tamanho_item == tamanho_camisa.upper():
                novo_qntd = qntd + delta * 3
            elif "camisa" not in nome_item:
                novo_qntd = qntd + delta * 1
            else:
                continue
            if novo_qntd < 0:
                raise ValueError(f"Estoque insuficiente para item {item['item']} ({tamanho_item})")
            item["qntd"] = str(novo_qntd)
    write_csv(EstoqueItem, dados)


def validar_estoque_para_kit(id_kit: str, tamanho_camisa: str) -> bool:
    dados = read_csv(EstoqueItem)
    itens_do_kit = [item for item in dados if item["id_kit"] == id_kit]
    
    camisa_ok = False
    outros_ok = True

    for item in itens_do_kit:
        qntd = int(item["qntd"])
        nome_item = item["item"].lower()
        tamanho_item = item.get("tamanho_camisa", "").upper()

        if "camisa" in nome_item and tamanho_item == tamanho_camisa.upper():
            camisa_ok = qntd >= 3
        elif "camisa" not in nome_item and qntd < 1:
            outros_ok = False

    return camisa_ok and outros_ok


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
    if not getattr(novo_registro, chave_id):
        setattr(novo_registro, chave_id, gerar_id(modelo))
    if modelo == Colaborador:
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