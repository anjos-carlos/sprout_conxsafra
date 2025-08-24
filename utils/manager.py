import csv
import os
from dataclasses import asdict, fields
from typing import List, Type
from .models import Agencia, Kit, EstoqueItem, Usuario, Colaborador


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")


# DICIONARIO PADRÃO DAS CLASSES
MODEL_FILE_MAP = {
    Agencia: "agencias.csv",
    Kit: "kits_cadastrados.csv",
    EstoqueItem: "estoque.csv",
    Usuario: "usuarios.csv",
    Colaborador: "colaboradores.csv",
}


### FUNÇÕES DE APOIO
def read_csv(file_name):
    path = os.path.join(DATA_DIR, file_name)
    data = []
    if not os.path.exists(path):
        return []  # se não existir, retorna lista vazia
    with open(path, mode="r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data

def write_csv(file_name, data, modelo):
    path = os.path.join(DATA_DIR, file_name)
    fieldnames = [f.name for f in fields(modelo)]
    with open(path, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)

def dicts_to_objects(data: List[dict], modelo: Type):
    objs = []
    for d in data:
        clean_d = {k: (v if v != '' else None) for k, v in d.items()}
        objs.append(modelo(**clean_d))
    return objs

def objects_to_dicts(objs: List):
    return [asdict(o) for o in objs]

def get_file_for_model(modelo: Type) -> str:
    return MODEL_FILE_MAP[modelo]


### FUNÇÃO DE VERIFICAÇÃO
def verificar_campos(modelo: Type, dados: dict) -> bool:
    modelo_fields = [f.name for f in fields(modelo)]
    preenchidos = [k for k, v in dados.items() if v is not None and v != ""]
    return len(preenchidos) <= len(modelo_fields)


### FUNÇÕES DO SISTEMA
def listar_registros(modelo: Type) -> List:
    file_name = get_file_for_model(modelo)
    return dicts_to_objects(read_csv(file_name), modelo)

def adicionar_registro(novo_registro, modelo: Type):
    file_name = get_file_for_model(modelo)
    dados = read_csv(file_name)
    dados.append(asdict(novo_registro))
    write_csv(file_name, dados, modelo)

def atualizar_registro(chave, valor_chave, novos_dados, modelo: Type):
    file_name = get_file_for_model(modelo)
    dados = read_csv(file_name)
    for d in dados:
        if d.get(chave) == valor_chave:
            d.update({k: v for k, v in novos_dados.items() if v is not None})
    write_csv(file_name, dados, modelo)

def remover_registro(chave, valor_chave, modelo: Type):
    file_name = get_file_for_model(modelo)
    dados = read_csv(file_name)
    dados = [d for d in dados if d.get(chave) != valor_chave]
    write_csv(file_name, dados, modelo)

def buscar_registro(chave, valor_chave, modelo: Type):
    file_name = get_file_for_model(modelo)
    dados = read_csv(file_name)
    filtrados = [d for d in dados if d.get(chave) == valor_chave]
    return dicts_to_objects(filtrados, modelo)

def filtrar_registros(modelo: Type, **criterios):
    file_name = get_file_for_model(modelo)
    dados = read_csv(file_name)
    filtrados = []
    for d in dados:
        if all(d.get(campo) == str(valor) for campo, valor in criterios.items()):
            filtrados.append(d)
    return dicts_to_objects(filtrados, modelo)

def ordenar_registros(modelo: Type, chave, reverso=False):
    objs = dicts_to_objects(read_csv(get_file_for_model(modelo)), modelo)
    return sorted(objs, key=lambda x: getattr(x, chave) or "", reverse=reverso)

def paginar_registros(registros: List, pagina=1, tamanho_pagina=10):
    inicio = (pagina - 1) * tamanho_pagina
    fim = inicio + tamanho_pagina
    return registros[inicio:fim]
