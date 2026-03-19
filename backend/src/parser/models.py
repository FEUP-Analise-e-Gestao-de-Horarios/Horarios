from pydantic import BaseModel, field_validator, model_validator


class ParAulasSimultaneas(BaseModel):
    """
    Validation model for a pair of simultaneous classes.
    Each pair consists of two class IDs and two class group codes.
    """

    aula1: int
    aula2: int
    turma1: str
    turma2: str

    @model_validator(mode="before")
    @classmethod
    def aceitar_lista(cls, v: object) -> object:
        """Accept the legacy frontend format [aula1, aula2, turma1, turma2]."""
        if isinstance(v, (list, tuple)) and len(v) == 4:
            return {"aula1": v[0], "aula2": v[1], "turma1": v[2], "turma2": v[3]}
        return v

    @field_validator("aula1", "aula2")
    @classmethod
    def ids_positivos(cls, v: int) -> int:
        if v <= 0:
            msg = "Aula ID must be a positive integer"
            raise ValueError(msg)
        return v


class AulasSimultaneasInput(BaseModel):
    """
    Validation model for the request body of guardar_aulas_em_paralelo.
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
