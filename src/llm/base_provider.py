from abc import ABC, abstractmethod
from typing import Dict, Any


class ILLMProvider(ABC):
    """
    Contrat abstrait (Interface SOLID) pour tout fournisseur d'inférence IA.
    Garantit l'interchangeabilité (LSP) entre IA locale et API distante.
    """

    @abstractmethod
    def generer_narration(self, prompt: str, num_ctx: int = 2048) -> Dict[str, Any]:
        """
        Envoie le prompt compressé et retourne un dictionnaire standardisé :
        {
            "texte": str,
            "tokens_generes": int,
            "tokens_par_sec": float,
            "duree_sec": float,
            "source": str
        }
        """
        pass
