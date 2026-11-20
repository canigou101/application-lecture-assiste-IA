import random
from enum import Enum
from typing import Tuple, Optional
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
        Tranche entre une action d'observation neutre et une action impactant l'intrigue.
        """
        mots_cles_neutres = ["scrute", "regarde", "observe", "examine", "écoute", "inspecte"]
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
    def evaluer_jet(score_total: float, difficulte: int = 20) -> ResultatAction:
        """Détermine l'issue parmi les 4 paliers du JDR."""
        if score_total <= 0:
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
        
        # Bonus de cohérence si la cible a un angle mort
        bonus_coherence = 0
        if cote_attaque == "droite" and "borgne_droit" in cible.traits_physiques:
            bonus_coherence = 2
        elif cote_attaque == "gauche" and "borgne_gauche" in cible.traits_physiques:
            bonus_coherence = 2

        facteur_base = attaquant.stats.force + attaquant.stats.stat_arme + bonus_coherence
        multiplicateur = attaquant.stats.chance + attaquant.stats.dext + malus
        
        degats_calcules = facteur_base * multiplicateur
        score_jet = de + degats_calcules
        resultat = self.evaluer_jet(score_jet, difficulte=25)

        # Si le personnage est trop mauvais (multiplicateur négatif), il se blesse lui-même
        auto_degats = abs(degats_calcules) if degats_calcules < 0 else 0

        return {
            "autorise": True,
            "jet_de": de,
            "degats": max(0, degats_calcules),
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
        resultat = self.evaluer_jet(de + score_seduction, difficulte=20)
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
        resultat = self.evaluer_jet(de + score_vol, difficulte=20)
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
        resultat = self.evaluer_jet(de + score_alt, difficulte=25)
        return {"jet_de": de, "score": score_alt, "resultat": resultat}
