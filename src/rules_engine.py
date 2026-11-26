import random
import re
from enum import Enum
from typing import Tuple, Optional, List
from src.models import Personnage


class ResultatAction(Enum):
    ECHEC_CUISANT = "Échec cuisant"
    SIMPLE_ECHEC = "Simple échec"
    REUSSITE_SIMPLE = "Réussite simple"
    FRANCHE_REUSSITE = "Franche réussite"


class MoteurReglesJDR:

    @staticmethod
    def est_action_avec_consequence(action_texte: str) -> bool:
        """
        Tranche entre une action d'observation/déplacement neutre et une action impactant l'intrigue.
        """
        mots_cles_neutres = [
            "scrute", "regarde", "observe", "examine", "écoute", "inspecte",
            "balade", "promène", "marche", "déplace", "flâne", "contemple"
        ]
        action_lower = action_texte.lower()
        for mot in mots_cles_neutres:
            if mot in action_lower:
                return False
        return True

    @staticmethod
    def verifier_autorisation_attaque(attaquant: Personnage, cible: Personnage) -> Tuple[bool, str]:
        """
        Règle de comportement :
        - Un perso 'gentil' ne peut pas attaquer un allié.
        - Un perso 'méchant' peut attaquer alliés comme ennemis.
        """
        est_allie = cible.id in attaquant.relations.allies
        if attaquant.caractere == "gentil" and est_allie:
            return False, f"{attaquant.nom} est gentil et refuse d'attaquer son allié {cible.nom}."
        return True, "Action autorisée."

    @staticmethod
    def calculer_est_mon_ennemi(p1: Personnage, p2: Personnage) -> int:
        """
        Calcule : (alliés communs * +1) + (mes ennemis qui sont ses alliés * -1)
        """
        allies_p1 = set(p1.relations.allies)
        ennemis_p1 = set(p1.relations.ennemis)
        allies_p2 = set(p2.relations.allies)

        allies_communs = len(allies_p1.intersection(allies_p2))
        ennemis_chez_ses_allies = len(ennemis_p1.intersection(allies_p2))

        return (allies_communs * 1) + (ennemis_chez_ses_allies * -1)

    @staticmethod
    def evaluer_jet(score_total: float, difficulte: int = 20, jet_de: Optional[int] = None) -> ResultatAction:
        """Détermine l'issue parmi les 4 paliers du JDR (avec échec critique sur un 1 naturel)."""
        if jet_de == 1 or score_total <= 0:
            return ResultatAction.ECHEC_CUISANT
        elif score_total < difficulte:
            return ResultatAction.SIMPLE_ECHEC
        elif score_total < difficulte * 1.5:
            return ResultatAction.REUSSITE_SIMPLE
        else:
            return ResultatAction.FRANCHE_REUSSITE
    def calculer_degats(
        self,
        attaquant: Personnage,
        cible: Personnage,
        cote_attaque: str = "face",
        malus: int = 0,
        jet_de: Optional[int] = None
    ) -> dict:
        """
        Formule : Dégâts = (force + statArme) * (chance + dext + malus)
        Intègre la cohérence physique (ex: cible borgne du côté droit).
        """
        autorise, raison = self.verifier_autorisation_attaque(attaquant, cible)
        if not autorise:
            return {"autorise": False, "raison": raison, "degats": 0}

        de = jet_de if jet_de is not None else random.randint(1, 20)

        bonus_coherence = 0
        if cote_attaque == "droite" and "borgne_droit" in cible.traits_physiques:
            bonus_coherence = 2
        elif cote_attaque == "gauche" and "borgne_gauche" in cible.traits_physiques:
            bonus_coherence = 2

        facteur_base = attaquant.stats.force + attaquant.stats.stat_arme + bonus_coherence
        multiplicateur = attaquant.stats.chance + attaquant.stats.dext + malus

        degats_calcules = facteur_base * multiplicateur
        score_jet = de + degats_calcules
        resultat = self.evaluer_jet(score_jet, difficulte=25, jet_de=de)

        if resultat == ResultatAction.ECHEC_CUISANT:
            degats_finaux = 0
        else:
            degats_finaux = max(0, degats_calcules)

        auto_degats = abs(degats_calcules) if degats_calcules < 0 else 0

        return {
            "autorise": True,
            "jet_de": de,
            "degats": degats_finaux,
            "auto_degats": auto_degats,
            "resultat": resultat
        }

    def calculer_seduction(
        self,
        initiateur: Personnage,
        cible: Personnage,
        malus: int = 0,
        jet_de: Optional[int] = None
    ) -> dict:
        """
        Formule : Séduction = (charisme + statsCosmetics) * (estMonEnnemi + chance + malus)
        """
        de = jet_de if jet_de is not None else random.randint(1, 20)
        score_relation = self.calculer_est_mon_ennemi(initiateur, cible)

        score_seduction = (initiateur.stats.charisme + initiateur.stats.stat_cosmetics) * (
            score_relation + initiateur.stats.chance + malus
        )
        resultat = self.evaluer_jet(de + score_seduction, difficulte=20, jet_de=de)
        return {"jet_de": de, "score": score_seduction, "resultat": resultat}

    def calculer_vol(
        self,
        voleur: Personnage,
        malus: int = 0,
        jet_de: Optional[int] = None
    ) -> dict:
        """
        Formule : Vol = (discrétion + dext) * (chance + malus)
        """
        de = jet_de if jet_de is not None else random.randint(1, 20)
        score_vol = (voleur.stats.discretion + voleur.stats.dext) * (voleur.stats.chance + malus)
        resultat = self.evaluer_jet(de + score_vol, difficulte=20, jet_de=de)
        return {"jet_de": de, "score": score_vol, "resultat": resultat}

    def calculer_alteration_mentale(
        self,
        lanceur: Personnage,
        chance1: int,
        chance2: int,
        jet_de: Optional[int] = None
    ) -> dict:
        """
        Formule : Altération = (force mentale + chance1) * (stats potion/sorts + chance2 + dext)
        """
        de = jet_de if jet_de is not None else random.randint(1, 20)
        score_alt = (lanceur.stats.force_mentale + chance1) * (
            lanceur.stats.stat_magie_potion + chance2 + lanceur.stats.dext
        )
        resultat = self.evaluer_jet(de + score_alt, difficulte=25, jet_de=de)
        return {"jet_de": de, "score": score_alt, "resultat": resultat}
    def detecter_cible(self, action_texte: str, personnages_presents: List[Personnage], joueur: Personnage) -> Personnage:
        """Identifie le PNJ mentionné dans la phrase du joueur (ou prend un PNJ présent par défaut)."""
        action_lower = action_texte.lower()
        pnjs = [p for p in personnages_presents if p.id != joueur.id]

        for pnj in pnjs:
            if pnj.nom.lower() in action_lower:
                return pnj
            for partie_nom in pnj.nom.lower().split():
                if len(partie_nom) > 2 and partie_nom in action_lower:
                    return pnj

        return pnjs[0] if pnjs else joueur

    def analyser_et_resoudre_action_libre(
        self,
        action_texte: str,
        joueur: Personnage,
        personnages_presents: List[Personnage]
    ) -> dict:
        """
        Analyse une phrase libre du joueur, détecte l'intention et applique la bonne formule JDR.
        """
        action_lower = action_texte.lower()
        avec_consequence = self.est_action_avec_consequence(action_texte)

        if not avec_consequence:
            return {
                "avec_consequence": False,
                "type_action": "Exploration / Observation neutre",
                "verdict": "Action libre sans impact critique sur l'intrigue (aucun jet de dé requis)."
            }

        cible = self.detecter_cible(action_texte, personnages_presents, joueur)

        # 1. Détection d'une attaque, d'un coup ou d'une mise en garde armée
        mots_combat = [
            "attaque", "frappe", "tue", "assassine", "poignarde", "égorge",
            "blesse", "combats", "tire", "coup", "épée", "lame", "garde"
        ]
        if any(mot in action_lower for mot in mots_combat):
            cote = "face"
            if "droite" in action_lower or "droit" in action_lower:
                cote = "droite"
            elif "gauche" in action_lower:
                cote = "gauche"
            elif any(m in action_lower for m in ["silencieusement", "discrètement", "dos", "ombre", "discret"]):
                if "borgne_droit" in cible.traits_physiques:
                    cote = "droite"
                elif "borgne_gauche" in cible.traits_physiques:
                    cote = "gauche"

            res = self.calculer_degats(joueur, cible, cote_attaque=cote)
            if not res["autorise"]:
                return {
                    "avec_consequence": True,
                    "type_action": f"Attaque bloquée contre {cible.nom}",
                    "verdict": res["raison"]
                }

            info_furtivite = ""
            if any(m in action_lower for m in ["silencieusement", "discrètement", "discret"]):
                res_vol = self.calculer_vol(joueur)
                info_furtivite = f" | Approche furtive (jet {res_vol['jet_de']}) : {res_vol['resultat'].value}"

            return {
                "avec_consequence": True,
                "type_action": f"Combat / Action armée sur {cible.nom} (angle: {cote})",
                "verdict": (
                    f"Cible: {cible.nom} | Jet de dé: {res['jet_de']} | "
                    f"Dégâts: {res['degats']} -> {res['resultat'].value}{info_furtivite}"
                )
            }

        # 2. Détection d'un vol / pickpocket / infiltration
        mots_vol = ["vole", "dérober", "pickpocket", "fouille", "crochète", "faufile", "infiltre"]
        if any(mot in action_lower for mot in mots_vol):
            res = self.calculer_vol(joueur)
            return {
                "avec_consequence": True,
                "type_action": f"Discrétion / Vol sur {cible.nom}",
                "verdict": (
                    f"Cible: {cible.nom} | Jet de dé: {res['jet_de']} | "
                    f"Score discrétion: {res['score']} -> {res['resultat'].value}"
                )
            }

        # 3. Détection d'un sortilège / potion / altération mentale
        if re.search(r"\b(sortilège|magie|hypnotise|charme|potion|ensorcelle|manipule)\b", action_lower):
            res = self.calculer_alteration_mentale(joueur, chance1=joueur.stats.chance, chance2=1)
            return {
                "avec_consequence": True,
                "type_action": f"Altération mentale sur {cible.nom}",
                "verdict": (
                    f"Cible: {cible.nom} | Jet de dé: {res['jet_de']} | "
                    f"Score mental: {res['score']} -> {res['resultat'].value}"
                )
            }

        # 4. Par défaut (parler, hurler, négocier, convaincre, interagir socialement)
        res = self.calculer_seduction(joueur, cible)
        return {
            "avec_consequence": True,
            "type_action": f"Interaction sociale / Dialogue avec {cible.nom}",
            "verdict": (
                f"Interlocuteur: {cible.nom} | Jet de dé: {res['jet_de']} | "
                f"Score charisme/alliance: {res['score']} -> {res['resultat'].value}"
            )
        }
