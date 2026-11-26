import json
import os
from src.models import Scene, Personnage, Stats, Relations
from src.rules_engine import MoteurReglesJDR
from src.llm import ILLMProvider, OllamaProvider, OpenRouterProvider

TAILLE_CONTEXTE = 2048  # Fenêtre de contexte maîtrisée (num_ctx)


def charger_secrets() -> dict:
    """Charge la configuration locale (clé OpenRouter, IP Jetson) depuis secrets.json."""
    if os.path.exists("secrets.json"):
        with open("secrets.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def choisir_fournisseur_ia() -> ILLMProvider:
    """
    Permet à l'utilisateur de basculer entre confidentialité locale/LAN et API distante.
    Respecte le principe de Substitution de Liskov (LSP) via ILLMProvider.
    """
    secrets = charger_secrets()
    print("\n" + "-" * 65)
    print("   PARAMÈTRE DE CONFIDENTIALITÉ & FOURNISSEUR D'INFÉRENCE IA")
    print("-" * 65)
    print("  [1] Ollama Local (PC : http://localhost:11434) — 100% Privé")
    print("  [2] Ollama LAN   (Jetson Nano : port 2020)     — 100% Privé")
    print("  [3] OpenRouter   (API Cloud)                   — Haute vitesse")
    
    choix = input("\nSélectionnez le moteur IA [1/2/3] (Entrée pour 1) : ").strip() or "1"

    if choix == "2":
        ip_jetson = secrets.get("jetson_ip") or input("IP statique du Jetson Nano (ex: 192.168.1.45) : ").strip()
        modele = input("Modèle sur Jetson (Entrée pour 'qwen2.5:1.5b') : ").strip() or "qwen2.5:1.5b"
        return OllamaProvider(base_url=f"http://{ip_jetson}:2020", modele=modele)

    elif choix == "3":
        api_key = secrets.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            api_key = input("Entrez votre clé API OpenRouter (sk-or-...) : ").strip()
        modele = input("Modèle OpenRouter (Entrée pour 'qwen/qwen-2.5-7b-instruct:free') : ").strip() or "qwen/qwen-2.5-7b-instruct:free"
        return OpenRouterProvider(api_key=api_key, modele=modele)

    # Par défaut : Ollama sur la machine locale
    modele_local = input("Modèle Ollama local (Entrée pour 'qwen2.5:1.5b') : ").strip() or "qwen2.5:1.5b"
    return OllamaProvider(base_url="http://localhost:11434", modele=modele_local)


def initialiser_scenario() -> dict[str, Scene]:
    """Crée deux scènes distinctes pour démontrer le découpage et la compression de contexte."""
    joueur = Personnage(
        id="p_joueur",
        nom="Arthur",
        est_joueur=True,
        caractere="gentil",
        stats=Stats(force=5, dext=4, charisme=6, force_mentale=5, discretion=3, chance=2, stat_arme=3),
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

    scene_1 = Scene(
        scene_id="scene_01_bal",
        lieu="Salle de bal royale",
        niveau_danger=2,
        resume_telegraphique="Banquet royal. Arthur veille sur le Roi Aldric. L'assassin Vesper rôde près du buffet.",
        personnages_presents=[joueur, roi, assassin]
    )

    scene_2 = Scene(
        scene_id="scene_02_cachots",
        lieu="Cachots du château",
        niveau_danger=6,
        resume_telegraphique="Arthur a poursuivi Vesper dans les sous-sols sombres après la tentative d'empoisonnement.",
        personnages_presents=[joueur, assassin]
    )

    return {"1": scene_1, "2": scene_2}


def lancer_cli():
    moteur = MoteurReglesJDR()
    scenes = initialiser_scenario()
    scene_courante = scenes["1"]

    print("=" * 65)
    print("   MOTEUR NARRATIF JDR — CLI SOLID (LOCAL / JETSON / OPENROUTER)")
    print("=" * 65)

    # Choix initial du fournisseur IA
    provider: ILLMProvider = choisir_fournisseur_ia()

    while True:
        print(f"\n[SCÈNE ACTIVE : {scene_courante.scene_id.upper()}]")
        print("-" * 65)
        contexte_compresse = scene_courante.generer_contexte_llm()
        print("CONTEXTE COMPRESSÉ ENVOYÉ AU LLM (Économie de tokens) :")
        print(contexte_compresse)
        print("-" * 65)

        print("\nActions disponibles :")
        print("  [1] Scruter la pièce (Action neutre)")
        print("  [2] Attaquer Vesper sur son côté droit (Action avec conséquence)")
        print("  [3] Changer de scène -> Aller aux Cachots (Découpage contexte)")
        print("  [4] Changer de fournisseur IA (Switch Confidentialité / API)")
        print("  [q] Quitter")

        choix = input("\nVotre choix (ou tapez une action libre) : ").strip()

        if choix.lower() == "q":
            print("\nArrêt du moteur narratif.")
            break

        elif choix == "3":
            scene_courante = scenes["2"]
            print("\n>>> TRANSITION DE SCÈNE : Le Roi Aldric est retiré du contexte JSON.")
            continue

        elif choix == "4":
            provider = choisir_fournisseur_ia()
            print("\n>>> FOURNISSEUR IA MIS À JOUR (État de la scène conservé).")
            continue

        elif choix == "1":
            action_texte = "Je scrute la pièce avec attention."
        elif choix == "2":
            action_texte = "J'attaque Vesper sur sa droite !"
        else:
            action_texte = choix

        # 1. Filtrage de l'action par le moteur
        avec_consequence = moteur.est_action_avec_consequence(action_texte)
        print(f"\n[ANALYSE MOTEUR] Action avec conséquence sur l'intrigue : {'OUI' if avec_consequence else 'NON (Observation)'}")

        verdict_regles = "Aucune mécanique requise (description simple)."

        # 2. Résolution JDR si conséquence
        if avec_consequence:
            joueur = scene_courante.personnages_presents[0]
            cible = scene_courante.personnages_presents[-1]
            res = moteur.calculer_degats(joueur, cible, cote_attaque="droite")
            verdict_regles = (
                f"Jet de dé: {res['jet_de']} | Dégâts infligés: {res['degats']} "
                f"(Bonus angle mort borgne appliqué) -> {res['resultat'].value}"
            )
            print(f"[RÈGLES JDR]     {verdict_regles}")

        # 3. Appel au fournisseur IA actif (Ollama PC, Jetson LAN ou OpenRouter)
        prompt_final = (
            f"{contexte_compresse}\n"
            f"ACTION JOUEUR: {action_texte}\n"
            f"VERDICT MOTEUR: {verdict_regles}\n"
            f"Consigne: Décris la suite en 2 phrases maximum."
        )

        print(f"\n[INFÉRENCE IA]   Envoi vers le fournisseur actif (num_ctx: {TAILLE_CONTEXTE})...")
        try:
            reponse_ia = provider.generer_narration(prompt_final, num_ctx=TAILLE_CONTEXTE)
            print(
                f"[MÉTRIQUES]      Source: {reponse_ia['source']} | "
                f"Vitesse: {reponse_ia['tokens_par_sec']} tokens/s "
                f"({reponse_ia['tokens_generes']} tokens en {reponse_ia['duree_sec']}s)"
            )
            print(f"\n[NARRATEUR IA]   « {reponse_ia['texte']} »\n")
        except Exception as err:
            print(f"\n[ERREUR IA]      {err}")
            print("                 Utilisez l'option [4] pour basculer sur un autre fournisseur.\n")

        print("=" * 65)


if __name__ == "__main__":
    lancer_cli()
