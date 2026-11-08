class ARLError(Exception):
    """Erreur attendue"""


class ConfigurationError(ARLError):
    """Réglage absent ou invalide (variable d'environnement, fournisseur inconnu...)"""


class SupplierError(ARLError):
    """Le service de modèle est injoignable ou refuse la requête."""