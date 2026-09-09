# Validation du 9 septembre 2026

Environnement : Windows x64, Python 3.10.6, Pillow 12.3.0, PySide6 6.11.0, PyInstaller 6.20.0.

## Tests automatisés

Commande : `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`

**9 tests réussis**, en 8,182 secondes lors de la dernière exécution.

- Paysage 6000 × 4000 → 5332 × 3999 ; portrait 4000 × 6000 → 3999 × 5332.
- 4:3 et 3:4 conservés ; carré orienté paysage.
- Ratio entier exact, rectangle maximal et centrage vérifiés sur toutes les dimensions de 4 à 79 pixels par axe.
- Huit orientations EXIF, position de pixels repères, conservation du profil ICC et du nom du photographe, suppression du tag Orientation.
- JPEG qualité 100 vérifiée par les tables de quantification ; absence de sous-échantillonnage ; empreintes des originaux inchangées.
- PNG transparent composé sur blanc, TIFF/TIF, WEBP, JPEG/JPG, noms Unicode et collisions de sortie.
- Recherche récursive ou simple, exclusion des exports et doublons, sources de plusieurs dossiers.
- Fichier corrompu, image trop petite, TIFF multipage et TIFF 16 bits signalés sans interrompre le traitement suivant.
- Interface Qt : événements de glisser-déposer de fichiers et dossier, worker, progression, Clear et fin de batch avec deux réussites et une erreur attendue.

Capture de contrôle : `test-results/gui-tested.png`.

## Exécutable

Compilation PyInstaller `--onefile --windowed` réussie : `dist/PhotoCrop4x3.exe`.

Lancement réel de l'exécutable réussi. La fenêtre « 4:3 Photo Crop », la zone d'ajout, la liste, les boutons et le statut Ready ont été observés via capture et arbre d'accessibilité Windows.

Limite de cette vérification : le service de contrôle Windows a retourné `failed to activate captured window`, y compris après une tentative de récupération. Aucun batch par clic n'a donc été exécuté dans le binaire compilé. Le batch et les événements drag & drop ont été testés avec succès dans l'application Qt depuis les sources.

Un petit dossier d'essai synthétique est disponible dans `test-results/Essai été 東京` : un JPEG paysage, un PNG portrait transparent et un faux JPEG corrompu destiné à tester la gestion d'erreurs.
