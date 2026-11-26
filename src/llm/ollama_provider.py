import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any
from src.llm.base_provider import ILLMProvider


class OllamaProvider(ILLMProvider):
    """
    Fournisseur local ou LAN (PC local ou Jetson Nano).
    Impose une sortie JSON structurée et rédigée en français.
    """

    def __init__(self, base_url: str, modele: str):
        if not base_url or not base_url.strip():
            raise ValueError("L'URL du serveur Ollama (base_url) est requise.")
        if not modele or not modele.strip():
            raise ValueError("Le nom du modèle Ollama (modele) est requis.")
        self.endpoint = f"{base_url.strip().rstrip('/')}/api/generate"
        self.modele = modele.strip()

    def generer_narration(self, prompt: str, num_ctx: int = 2048) -> Dict[str, Any]:
        prompt_json = (
            "CONSIGNE DE LANGUE : Tu es un narrateur de JDR francophone. Rédige tout le texte uniquement en français.\n\n"
            f"{prompt}\n\n"
            "Réponds UNIQUEMENT avec un objet JSON valide respectant exactement cette structure en français :\n"
            '{"narration": "Récit immersif en français en 2 phrases maximum.", '
            '"nouveau_resume_telegraphique": "Résumé factuel très court en français.", '
            '"changement_scene_suggere": false}'
        )

        payload = {
            "model": self.modele,
            "prompt": prompt_json,
            "format": "json",
            "stream": False,
            "options": {
                "num_ctx": num_ctx,
                "num_predict": 150,
                "temperature": 0.7
            }
        }

        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        debut = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                data = json.loads(response.read().decode("utf-8"))
                eval_count = data.get("eval_count", 0)
                eval_duration_ns = data.get("eval_duration", 0)

                if eval_duration_ns > 0:
                    duree_sec = eval_duration_ns / 1e9
                else:
                    duree_sec = max(time.perf_counter() - debut, 0.01)

                tokens_par_sec = eval_count / duree_sec if duree_sec > 0 else 0.0
                reponse_brute = data.get("response", "").strip()

                try:
                    donnees_structurees = json.loads(reponse_brute)
                except json.JSONDecodeError:
                    donnees_structurees = {
                        "narration": reponse_brute,
                        "nouveau_resume_telegraphique": "",
                        "changement_scene_suggere": False
                    }

                return {
                    "texte": donnees_structurees.get("narration", reponse_brute),
                    "donnees_json": donnees_structurees,
                    "tokens_generes": eval_count,
                    "tokens_par_sec": round(tokens_par_sec, 2),
                    "duree_sec": round(duree_sec, 2),
                    "source": f"OLLAMA LOCAL/LAN ({self.modele})"
                }
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Erreur HTTP Ollama ({e.code}) sur {self.endpoint} : {detail}")
        except urllib.error.URLError as e:
            raise ConnectionError(f"Impossible de joindre Ollama sur {self.endpoint} : {e}")
