from pydantic import BaseModel, field_validator


class ParAulasSimultaneas(BaseModel):
    """
    Modelo de validação para um par de aulas simultâneas.
    Cada par é composto por dois IDs de aula e dois códigos de turma.
    """

    aula1: int
    aula2: int
    turma1: str
    turma2: str

    @field_validator("aula1", "aula2")
    @classmethod
    def ids_positivos(cls, v: int) -> int:
        if v <= 0:
            msg = "ID de aula deve ser um inteiro positivo"
            raise ValueError(msg)
        return v


class AulasSimultaneasInput(BaseModel):
    """
    Modelo de validação para o corpo do pedido de guardar aulas em paralelo.
    """

    pares: list[ParAulasSimultaneas]


class Aula:
    """
    Classe auxiliar para encontrar aulas duplicadas
    """

    def __init__(self, dictionary):
        for key, value in dictionary.items():
            setattr(self, key, value)

    def __hash__(self):
        items = []
        for key, value in sorted(self.__dict__.items()):
            if isinstance(value, list):
                value = tuple(value)
            items.append((key, value))
        return hash(tuple(items))

    def __eq__(self, other):
        if isinstance(other, Aula):
            return self.__dict__ == other.__dict__
        return False
