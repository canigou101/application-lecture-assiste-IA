import os
from pathlib import Path
from src.models import Scene, Personnage, Stats, Relations
from src.rules_engine import MoteurReglesJDR
from src.llm import ILLMProvider, OllamaProvider, OpenRouterProvider

TAILLE_CONTEXTE = 2048  # Fenêtre de contexte maîtrisée (num_ctx)
DOSSIER_RACINE = Path(__file__).resolve().parent


def charger_env(filepath: Path = DOSSIER_RACINE / ".env") -> list[str]:
    """Charge les variables du fichier .env situé à la racine du projet."""
    cles_chargees: list[str] = []
    if not filepath.exists():
        return cles_chargees
    with open(filepath, "r", encoding="utf-8") as f:
        for ligne in f:
            ligne = ligne.strip()
            if not ligne or ligne.startswith("#") or "=" not in ligne:
                continue
            cle, valeur = ligne.split("=", 1)
            cle_propre = cle.strip()
            valeur_propre = valeur.strip().strip('"').strip("'")
            os.environ[cle_propre] = valeur_propre
            cles_chargees.append(cle_propre)
    return cles_chargees


def obtenir_url_jetson(cles_env: list[str]) -> str:
    """Récupère l'URL du Jetson Nano depuis le .env (URL complète ou IP seule)."""
    url = os.getenv("OLLAMA_JETSON_URL") or os.getenv("JETSON_URL")
    if url:
        return url.strip()

    ip = (os.getenv("JETSON_IP") or os.getenv("IP_JETSON") or "").strip()
    port = (os.getenv("JETSON_PORT") or os.getenv("PORT_JETSON") or "2020").strip()
    if ip:
        if ip.startswith("http"):
            return ip
        return f"http://{ip}:{port}"

    raise ValueError(
        f"Configuration Jetson manquante dans {DOSSIER_RACINE / '.env'}.\n"
        f"Clés actuellement détectées dans votre .env : {cles_env}"
    )


def choisir_fournisseur_ia() -> ILLMProvider:
    """Sélectionne le fournisseur IA en lisant directement le fichier .env."""
    cles_env = charger_env()

    print("\n" + "-" * 65)
    print("   PARAMÈTRE DE CONFIDENTIALITÉ & FOURNISSEUR D'INFÉRENCE IA")
    print("-" * 65)
    print("  [1] Ollama Local (PC)          — 100% Privé")
    print("  [2] Ollama LAN   (Jetson Nano) — 100% Privé")
    print("  [3] OpenRouter   (API Cloud)   — Haute vitesse")

    choix = input("\nSélectionnez le moteur IA [1/2/3] (Entrée pour 1) : ").strip() or "1"

    if choix == "2":
        url_jetson = obtenir_url_jetson(cles_env)
        modele_jetson = os.getenv("OLLAMA_JETSON_MODEL") or os.getenv("OLLAMA_MODEL") or "qwen2.5:1.5b"
        print(f"-> Connexion au Jetson sur : {url_jetson} ({modele_jetson})")
        return OllamaProvider(base_url=url_jetson, modele=modele_jetson)

    elif choix == "3":
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError(f"Clé OPENROUTER_API_KEY manquante dans {DOSSIER_RACINE / '.env'}.")
        modele_impose = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.2-3b-instruct:free")
        print(f"-> Modèle OpenRouter imposé : {modele_impose}")
        return OpenRouterProvider(api_key=api_key, modele=modele_impose)

    url_locale = os.getenv("OLLAMA_LOCAL_URL")
    modele_local = os.getenv("OLLAMA_LOCAL_MODEL") or os.getenv("OLLAMA_MODEL") or "qwen2.5:1.5b"
    if not url_locale:
        raise ValueError(f"Variable OLLAMA_LOCAL_URL manquante dans {DOSSIER_RACINE / '.env'}.")
    print(f"-> Connexion locale sur : {url_locale} ({modele_local})")
    return OllamaProvider(base_url=url_locale, modele=modele_local)


def initialiser_scenario() -> dict[str, Scene]:
    """Crée les scènes de départ pour la narration libre."""
    joueur = Personnage(
        id="p_joueur",
        nom="Arthur",
        est_joueur=True,
        caractere="gentil",
        stats=Stats(force=5, dext=4, charisme=6, force_mentale=5, discretion=6, chance=2, stat_arme=3, stat_cosmetics=2),
        relations=Relations(allies=["pnj_roi"], ennemis=["pnj_assassin"])
    )

    roi = Personnage(
        id="pnj_roi",
        nom="Roi Aldric",
        est_joueur=False,
        caractere="gentil",
        stats=Stats(force=4, dext=2, charisme=8, force_mentale=7, discretion=1, chance=3),
        relations=Relations(allies=["p_joueur"], ennemis=["pnj_assassin"])
    )

    assassin = Personnage(
        id="pnj_assassin",
        nom="Vesper",
        est_joueur=False,
        caractere="mechant",
        traits_physiques=["borgne_droit"],
        objectif_cache="Empoisonner la coupe du roi",
        stats=Stats(force=6, dext=7, charisme=3, force_mentale=4, discretion=8, chance=2, stat_arme=4),
        relations=Relations(allies=[], ennemis=["pnj_roi"])
    )

    scene_bal = Scene(
        scene_id="scene_01_bal",
        lieu="Salle de bal royale",
        niveau_danger=2,
        resume_telegraphique="Banquet royal. Arthur veille sur le Roi Aldric. L'assassin Vesper rôde près du buffet.",
        personnages_presents=[joueur, roi, assassin]
    )

    scene_cachots = Scene(
        scene_id="scene_02_cachots",
        lieu="Cachots du château",
        niveau_danger=6,
        resume_telegraphique="Sous-sols sombres du château où Vesper tente de fuir.",
        personnages_presents=[joueur, assassin]
    )

    return {"bal": scene_bal, "cachots": scene_cachots}
def lancer_cli():
    moteur = MoteurReglesJDR()
    scenes = initialiser_scenario()
    scene_courante = scenes["bal"]

    print("=" * 65)
    print("   MOTEUR NARRATIF JDR — MODE LIBRE & RÈGLES DYNAMIQUES")
    print("=" * 65)

    provider: ILLMProvider = choisir_fournisseur_ia()

    while True:
        print(f"\n[SCÈNE ACTIVE : {scene_courante.scene_id.upper()}]")
        print("-" * 65)
        contexte_compresse = scene_courante.generer_contexte_llm()
        print("CONTEXTE COMPRESSÉ ENVOYÉ AU LLM (Économie de tokens) :")
        print(contexte_compresse)
        print("-" * 65)
        print("Commandes système : /scene (changer de lieu) | /ia (changer d'IA) | /quit")

        action_texte = input("\nQue fait Arthur ? > ").strip()

        if not action_texte:
            continue

        if action_texte.lower() in ["/quit", "/q", "quitter"]:
            print("\nArrêt du moteur narratif.")
            break

        if action_texte.lower() == "/ia":
            provider = choisir_fournisseur_ia()
            print("\n>>> FOURNISSEUR IA MIS À JOUR.")
            continue

        if action_texte.lower() == "/scene" or "cachot" in action_texte.lower():
            if scene_courante.scene_id == "scene_01_bal":
                scene_courante = scenes["cachots"]
                print("\n>>> TRANSITION DE SCÈNE : Arrivée aux Cachots (Roi Aldric retiré du contexte).")
            else:
                scene_courante = scenes["bal"]
                print("\n>>> TRANSITION DE SCÈNE : Retour dans la Salle de bal royale.")
            if action_texte.lower() == "/scene":
                continue

        # Récupération sans modifier la liste des personnages présents
        joueur = next((p for p in scene_courante.personnages_presents if p.est_joueur), scene_courante.personnages_presents[0])
        analyse = moteur.analyser_et_resoudre_action_libre(
            action_texte=action_texte,
            joueur=joueur,
            personnages_presents=scene_courante.personnages_presents
        )

        print(f"\n[ANALYSE MOTEUR] {analyse['type_action']} (Conséquence : {'OUI' if analyse['avec_consequence'] else 'NON'})")
        print(f"[RÈGLES JDR]     {analyse['verdict']}")

        prompt_final = (
            f"{contexte_compresse}\n"
            f"PROTAGONISTE INCARNÉ PAR LE JOUEUR : {joueur.nom}\n"
            f"ACTION LIBRE DE {joueur.nom.upper()} : {action_texte}\n"
            f"VERDICT DU MOTEUR DE RÈGLES : {analyse['verdict']}\n"
            f"Consigne : Raconte ce que fait {joueur.nom} et la réaction de la scène en français, en 2 phrases maximum, en respectant strictement le verdict."
        )

        print(f"\n[INFÉRENCE IA]   Envoi vers le fournisseur actif (num_ctx: {TAILLE_CONTEXTE})...")
        try:
            reponse_ia = provider.generer_narration(prompt_final, num_ctx=TAILLE_CONTEXTE)
            print(
                f"[MÉTRIQUES]      Source: {reponse_ia['source']} | "
                f"Vitesse: {reponse_ia['tokens_par_sec']} tokens/s "
                f"({reponse_ia['tokens_generes']} tokens en {reponse_ia['duree_sec']}s)"
            )
            print(f"\n[NARRATEUR IA]   « {reponse_ia['texte']} »")

            donnees_json = reponse_ia.get("donnees_json", {})
            nouveau_resume = donnees_json.get("nouveau_resume_telegraphique")
            if nouveau_resume:
                scene_courante.resume_telegraphique = nouveau_resume
                print(f"[MÉMOIRE JSON]   Résumé télégraphique mis à jour : {nouveau_resume}\n")

        except Exception as err:
            print(f"\n[ERREUR IA]      {err}")
            print("                 Tapez /ia pour basculer sur un autre fournisseur.\n")

        print("=" * 65)


if __name__ == "__main__":
    lancer_cli()
