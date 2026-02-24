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
