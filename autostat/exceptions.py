"""Application-specific errors with concise user-facing messages."""


class AutoStatErreur(Exception):
    """Base class for expected AutoStat failures."""


class FichierDonneesErreur(AutoStatErreur):
    """A source file or archive could not be read."""


class LigneInvalideErreur(AutoStatErreur):
    """A data row failed validation."""

    def __init__(self, numero: int, motif: str) -> None:
        self.numero = numero
        self.motif = motif
        super().__init__(f"Ligne {numero} : {motif}")
