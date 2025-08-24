from dataclasses import dataclass
from typing import Optional

@dataclass
class Agencia:
    id_agencia: Optional[int] = None
    nome_agencia: str = ""
    local_envio: str = ""

@dataclass
class Kit:
    id_kit: Optional[int] = None
    nome_kit: str = ""

@dataclass
class EstoqueItem:
    id_item: Optional[int] = None
    item: str = ""
    tamanho_camisa: Optional[str] = None
    id_kit: int = 0
    qntd: int = 0

@dataclass
class Usuario:
    id_usuario: Optional[int] = None
    usuario: str = ""
    senha: str = ""
    nome: str = ""
    email: str = ""
    id_classe: Optional[int] = None
    nome_classe: Optional[str] = None

@dataclass
class Colaborador:
    id_colaborador: Optional[int] = None
    nome_colaborador: str = ""
    email_colaborador: str = ""
    id_gestor: Optional[int] = None
    id_kit: Optional[int] = None
    data_admissao: Optional[str] = None
    tamanho_camisa: Optional[str] = None
    id_agencia: Optional[int] = None
    situacao: Optional[str] = None