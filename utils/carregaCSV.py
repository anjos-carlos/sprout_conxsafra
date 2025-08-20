import os

class CarregaCSV:
    def __init__(self, name, **params):
        self.name = name
        self.local = os.path.abspath(params.get('path', os.getcwd()))
        self.caminho = os.path.join(self.local, self.name)
        self.extrair_dados()

    def extrair_dados(self):
        with open(self.caminho, 'r') as arquivo:
            return arquivo.read().splitlines()