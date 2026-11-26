import json
import re
import time
import urllib.request
import urllib.error
from typing import Dict, Any, List
from src.llm.base_provider import ILLMProvider


class OpenRouterProvider(ILLMProvider):
    """Fournisseur API distante via OpenRouter avec sortie JSON structurée en français."""

    BASE_URL = "https://openrouter.ai"
    CHAT_PATH = "/api/v1/chat/completions"
    MODELES_SECOURS: List[str] = [
        "meta-llama/llama-3.2-3b-instruct:free",
        "google/gemma-3-12b-it:free",
        "mistralai/mistral-7b-instruct:free"
    ]

    def __init__(
        self,
        api_key: str,
        modele: str = "meta-llama/llama-3.2-3b-instruct:free",
        app_name: str = "Application-Lecture-Assistee-IA"
    ):
        if not api_key or not api_key.strip():
            raise ValueError("Une clé API OpenRouter valide est requise.")
        self.api_key = api_key.strip()
        self.modele = modele.strip()
        self.app_name = app_name
        self.endpoint = self.BASE_URL + self.CHAT_PATH

    def _extraire_json(self, texte_brut: str) -> Dict[str, Any]:
        """Nettoie les éventuelles balises Markdown ```json et extrait l'objet JSON."""
        nettoye = re.sub(r"^```(?:json)?\s*|\s*```$", "", texte_brut.strip(), flags=re.IGNORECASE)
        try:
            return json.loads(nettoye)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", nettoye, flags=re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        return {
            "narration": nettoye,
            "nouveau_resume_telegraphique": "",
            "changement_scene_suggere": False
        }

    def _appeler_modele(self, modele_cible: str, prompt: str) -> Dict[str, Any]:
        payload = {
            "model": modele_cible,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Tu es le maître du jeu d'un JDR interactif exclusivement francophone. "
                        "RÈGLE ABSOLUE : Rédige toutes tes réponses uniquement en langue française (interdiction stricte d'utiliser l'anglais). "
                        "Réponds UNIQUEMENT avec un objet JSON valide suivant ce modèle exact : "
                        '{"narration": "Texte narratif immersif en français en 2 phrases maximum.", '
                        '"nouveau_resume_telegraphique": "Résumé factuel très court en français.", '
                        '"changement_scene_suggere": false}'
                    )
                },
                {
                    "role": "user",
                    "content": f"{prompt}\n\nRappel : Réponds uniquement en français dans le JSON."
                }
            ],
            "max_tokens": 800,
            "temperature": 0.7
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "OpenRouterPythonClient/1.0",
            "HTTP-Referer": "https://github.com",
            "X-Title": self.app_name
        }

        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        debut = time.perf_counter()
        with urllib.request.urlopen(req, timeout=60) as response:
            raw_body = response.read().decode("utf-8", errors="replace").strip()
            data = json.loads(raw_body)

            if "error" in data:
                raise RuntimeError(f"Erreur API OpenRouter : {data['error']}")

            duree_sec = max(time.perf_counter() - debut, 0.01)
            premier_choix = data["choices"].pop(0)
            message = premier_choix["message"]
            contenu = message.get("content")
            reponse_brute = str(contenu).strip() if contenu else ""

            if not reponse_brute:
                raise RuntimeError(f"Contenu vide renvoyé par {modele_cible}")

            donnees_structurees = self._extraire_json(reponse_brute)
            modele_utilise = data.get("model", modele_cible)
            usage = data.get("usage", {})
            tokens_generes = usage.get("completion_tokens", len(reponse_brute.split()))
            tokens_par_sec = tokens_generes / duree_sec

            return {
                "texte": donnees_structurees.get("narration", reponse_brute),
                "donnees_json": donnees_structurees,
                "tokens_generes": tokens_generes,
                "tokens_par_sec": round(tokens_par_sec, 2),
                "duree_sec": round(duree_sec, 2),
                "source": f"OPENROUTER API ({modele_utilise})"
            }

    def generer_narration(self, prompt: str, num_ctx: int = 2048) -> Dict[str, Any]:
        candidats = [self.modele] + [m for m in self.MODELES_SECOURS if m != self.modele]
        derniere_erreur = None

        for modele_cible in candidats:
            try:
                return self._appeler_modele(modele_cible, prompt)
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", errors="ignore")
                derniere_erreur = RuntimeError(f"Erreur HTTP OpenRouter ({e.code}) sur {modele_cible} : {detail[:200]}")
            except urllib.error.URLError as e:
                raise ConnectionError(f"Erreur réseau vers OpenRouter : {e}")
            except Exception as e:
                derniere_erreur = e

        raise RuntimeError(f"Échec sur tous les modèles OpenRouter tentés. Dernière erreur : {derniere_erreur}")
