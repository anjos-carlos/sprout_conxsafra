from dataclasses import dataclass
from typing import Optional

@dataclass
class Agencia:
    id_agencia: str = ""
    nome_agencia: str = ""
    local_envio: str = ""

@dataclass
class Kit:
    id_kit: str = ""
    nome_kit: str = ""
    id_item: str = ""
    item: str = ""
    tamanho_camisa: Optional[str] = None

@dataclass
class EstoqueItem:
    id_item: str = ""
    item: str = ""
    tamanho_camisa: Optional[str] = None
    id_kit: str = ""
    nome_kit: str = ""
    qntd: int = 0

@dataclass
class Usuario:
    id_usuario: str = ""
    usuario: str = ""
    senha: str = ""
    nome: str = ""
    email: str = ""
    id_classe: str = ""
    nome_classe: str = ""

@dataclass
class Colaborador:
    id_colaborador : str = ""
    nome_colaborador : str = ""
    email_colaborador : str = ""
    id_gestor : str = ""
    nome_gestor : str = ""
    email_gestor : str = ""
    id_kit : str = ""
    nome_kit : str = ""
    data_admissao : str = ""
    tamanho_camisa: Optional[str] = None
    id_agencia : str = ""
    nome_agencia : str = ""
    local_envio : str = ""
    situacao : str = ""