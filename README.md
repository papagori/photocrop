# 4:3 Photo Crop

Petite application desktop Windows en Python / PySide6. Recadrage centré automatique en **4:3 paysage** ou **3:4 portrait**, sans redimensionnement, sans étirement et sans bordures ajoutées.

## Tester directement sous Windows

Double-cliquer sur **`dist\PhotoCrop4x3.exe`**. Cet exécutable autonome Windows x64 embarque Python et ses dépendances : aucune installation Python nécessaire. Le premier lancement peut prendre quelques secondes pendant l'extraction des composants Qt.

1. Déposer plusieurs fichiers ou un dossier dans la zone centrale, ou cliquer pour choisir **Add files…** / **Add folder…**.
2. Cocher **Include subfolders** avant d'ajouter un dossier pour inclure ses sous-dossiers.
3. Cliquer **Process**. Les sorties sont écrites dans `4x3_cropped`, dans le dossier de chaque source.
4. Consulter les dimensions dans la liste et les chemins / erreurs dans le journal. **Clear** vide seulement la liste.

Les fichiers originaux restent intacts. Les collisions produisent `nom_2.jpg`, `nom_3.jpg`, etc., y compris lorsque deux sources ont le même nom mais des extensions différentes. Relancer Process produit de nouvelles copies. Les dossiers `4x3_cropped` sont exclus de la recherche ; les doublons et extensions incompatibles sont comptabilisés dans « skipped ». Les images déjà au bon ratio sont exportées sans recadrage et comptent comme traitées.

## Recadrage et qualité

L'orientation EXIF est appliquée avant toute décision. Un carré est paysage. Pour un ratio `a:b`, on calcule `k = min(largeur // a, hauteur // b)` et on garde le rectangle centré `a*k × b*k`. C'est le plus grand rectangle entier de ratio **exact** qui tient dans l'image. Aucun rééchantillonnage n'est effectué.

Ainsi, **6000 × 4000 → 5332 × 3999**, et **4000 × 6000 → 3999 × 5332**. Garder 5333 × 4000 serait légèrement différent de 4:3. Un pixel de décalage entre les marges est possible lorsque la différence est impaire.

Export Pillow : `quality=100`, `subsampling=0`, `optimize=True`. JPEG reste un format avec pertes, même à qualité 100 ; l'export réencode donc aussi les JPEG qui n'ont pas besoin de crop. La résolution n'est réduite que par le recadrage demandé. Les fichiers peuvent être volumineux.

Le profil ICC est conservé lorsque l'espace colorimétrique reste compatible ; RGB, niveaux de gris et CMYK restent dans leur espace. LAB est converti en sRGB avec gestion de couleur. La transparence est composée sur blanc avant export RGB. Les EXIF pertinents sont conservés autant que Pillow le permet, l'orientation est supprimée et les dimensions EXIF existantes sont corrigées. Les aperçus intégrés et les métadonnées propres à certains formats ne sont pas garantis.

Entrées : JPG/JPEG, PNG, TIFF/TIF, WEBP. Les images animées et TIFF multipages sont signalés en erreur plutôt que de perdre silencieusement les autres pages. Les images 16/32 bits sont signalées en erreur : une conversion JPEG 8 bits fidèle nécessite un choix de tonalité. Les images trop petites pour un ratio entier exact sont aussi signalées. Une erreur n'arrête pas le batch. Les chemins Unicode, accents, japonais et espaces sont pris en charge.

La recherche et le traitement tournent dans un QThread. Pendant une opération, les changements de liste et la fermeture sont désactivés ; attendre la fin du batch avant de fermer. Les chemins complets sont disponibles dans les info-bulles et peuvent être copiés depuis le journal.

## Lancer depuis les sources

Python **3.10 ou plus récent**, Windows x64 conseillé. Dans PowerShell, depuis ce dossier :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Tester et compiler un EXE autonome

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name PhotoCrop4x3 main.py
```

Ou exécuter `powershell -ExecutionPolicy Bypass -File .\build.ps1` pour préparer l'environnement, tester et compiler. Résultat : `dist\PhotoCrop4x3.exe`. Compiler sous Windows pour obtenir un EXE Windows. Il est non signé.

Tests : paysage 3:2, portrait 2:3, ratios existants, carré, huit orientations EXIF, ICC, JPEG haute qualité, transparence, PNG/TIFF/WEBP, collisions, intégrité des originaux, dossiers récursifs, Unicode, fichier corrompu, limites de formats, événements drag & drop Qt et batch dans le worker.

## Organisation

- `main.py` : point d'entrée.
- `cropper/gui.py` : interface et worker Qt.
- `cropper/discovery.py` : recherche, filtrage et dédoublonnage.
- `cropper/processing.py` : orientation, calcul du crop et gestion des erreurs individuelles.
- `cropper/export.py` : conversion de couleur, métadonnées et écriture JPEG exclusive.
- `tests/test_cropper.py` : tests automatisés sans dépendance de test additionnelle.

Références : [options JPEG de Pillow](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#jpeg), [compilation PyInstaller](https://pyinstaller.org/en/stable/usage.html).
