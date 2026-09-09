# Photo Crop — V2

Application desktop Windows en Python / PySide6 : recadrage centré selon l'orientation EXIF, ratio au choix, redimensionnement facultatif et export JPEG de qualité maximale.

## Tester directement

Double-cliquer sur **`dist\PhotoCropV2.exe`**. Cet exécutable Windows x64 embarque Python, Qt et Pillow : aucune installation nécessaire. Son démarrage peut prendre quelques secondes pendant l'extraction des composants.

1. Déposer plusieurs images ou un dossier, ou cliquer dans la zone centrale pour **Add files…** / **Add folder…**.
2. Cocher **Include subfolders** avant l'ajout pour inclure les sous-dossiers.
3. Choisir **Aspect Ratio**, **Output Size** et éventuellement **Allow Upscaling**.
4. Cliquer **Process** ; la liste et le journal affichent les dimensions, les sorties et les erreurs individuelles.

Les valeurs initiales restent **4:3**, **Original Resolution**, agrandissement désactivé. Le comportement initial est donc conservé par défaut. **Clear** vide uniquement la liste ; les réglages restent sélectionnés. Les menus sont verrouillés pendant le batch et ses réglages sont figés dans le worker.

Les JPEG sont toujours exportés dans **`4x3_cropped`**, à côté de chaque source, y compris avec les nouveaux ratios. Ce nom historique est conservé. Les originaux ne sont jamais écrasés. Les collisions produisent `nom_2.jpg`, `nom_3.jpg`, etc. Relancer Process crée de nouvelles copies. Les dossiers de sortie sont exclus de la recherche automatique.

## Aspect Ratio

Choix : **Original / No Crop**, **1:1**, **4:3**, **3:2**, **5:4**, **16:9**, **16:10**, **21:9**.

L'orientation EXIF est appliquée avant la décision. Une image plus haute que large est portrait ; sinon, elle est paysage. Le ratio est inversé pour les portraits : 4:3 → 3:4, 16:9 → 9:16, etc. Un carré est traité comme paysage.

**Original / No Crop** conserve l'image entière après orientation. Avec **Original Resolution**, aucun resize n'est effectué. Avec un preset de grand côté, la taille de sortie est ajustée avec l'arrondi au pixel indispensable.

## Output Size

Le menu est séparé en groupes dont les titres ne sont pas sélectionnables.

| Groupe | Choix |
| --- | --- |
| Original Resolution | Conserver toute la résolution restante après crop |
| Long Edge | 1K / 1024, 2K / 2048, 3K / 3072, 4K / 4096, 5K / 5120, 6K / 6144, 8K / 8192 px sur le grand côté |
| Photo Presets | 1200 × 800, 1500 × 1000, 2048 × 1365, 2400 × 1600, 3000 × 2000, 4000 × 3000, 4500 × 3000, 5000 × 3333, 6000 × 4000, 6000 × 4500 px |
| Video / Screen Presets | 1920 × 1080, 2560 × 1440, 3840 × 2160, 7680 × 4320 px |

**Long Edge** respecte le ratio choisi indépendamment. Le grand côté est exactement celui annoncé et le petit côté est arrondi au pixel le plus proche. Par exemple, 4096 px donne 4096 × 3072 en 4:3 et 4096 × 2304 en 16:9 ; les dimensions sont inversées en portrait. « 4K / 4096 px » est distinct du preset écran **3840 × 2160**.

Un **preset exact impose son ratio** et le sélectionne automatiquement dans Aspect Ratio, qui devient temporairement non modifiable. Par exemple : 3000 × 2000 → 3:2, 4000 × 3000 → 4:3, 3840 × 2160 → 16:9. Revenir à Original Resolution ou Long Edge permet de choisir librement le ratio. Les dimensions annoncées sont inversées pour les portraits.

2048 × 1365 et 5000 × 3333 sont seulement **approximativement 3:2** : le menu affiche temporairement `2048:1365 (approx. 3:2)` ou `5000:3333 (approx. 3:2)`. Le traitement utilise leur ratio réel pour garantir exactement la sortie annoncée. En quittant ces presets, Aspect Ratio revient à 3:2.

**Allow Upscaling** est désactivé par défaut. Si la taille demandée dépasse celle disponible **après crop**, le resize est ignoré : l'image garde toute sa résolution recadrée et la liste affiche **upscaling avoided**. Cela prime sur les dimensions d'un preset exact. Cocher l'option autorise l'agrandissement. Elle est inactive pour Original Resolution.

## Géométrie et qualité

Ordre : lecture → orientation EXIF → orientation réelle → crop centré → éventuel resize unique → JPEG.

Pour les ratios standards, réduits à `a:b`, le crop conserve `a*k × b*k`, avec `k = min(largeur // a, hauteur // b)`. C'est le plus grand rectangle entier de ratio exact. Ainsi **6000 × 4000 → 5332 × 3999** en 4:3, sans resize supplémentaire en Original Resolution. Un pixel de différence entre les marges est possible.

Pour les deux presets approximatifs, imposer des multiples entiers de 2048:1365 ou 5000:3333 ferait perdre inutilement une grande partie de l'image. Le crop conserve donc le plus grand rectangle arrondi au pixel. Lors du resize final, une correction de bord inférieure à un pixel ajuste le ratio exact sans étirement. Si l'agrandissement est refusé, on conserve ce rectangle entier : son ratio peut différer de la cible d'un arrondi d'un pixel.

Le resize utilise **`Image.Resampling.LANCZOS`**, en un seul appel depuis l'image recadrée, sans réduction intermédiaire (`reducing_gap=None`). Les tailles arrondies peuvent nécessiter une correction sous-pixel des bords pour éviter une déformation. Les palettes et images binaires sont converties avant filtrage afin d'éviter le filtre NEAREST forcé par Pillow. La transparence est composée sur blanc avant filtrage et export.

JPEG : **`quality=100`, `subsampling=0`, `optimize=True`**. JPEG reste avec pertes et l'export réencode aussi les sources déjà au bon ratio. Les fichiers peuvent être volumineux. Il n'y a ni bordures ajoutées ni étirement.

Le profil ICC est conservé lorsque l'espace de couleur reste compatible ; RGB, gris et CMYK restent dans leur espace. LAB est converti vers sRGB avec gestion de couleur. Les EXIF pertinents sont conservés autant que Pillow le permet, l'orientation est supprimée et les dimensions existantes sont mises à jour **après resize**. Les aperçus intégrés et métadonnées spécifiques à certains formats ne sont pas garantis.

Entrées : JPG/JPEG, PNG, TIFF/TIF, WEBP. Les images animées, TIFF multipages et images 16/32 bits sont signalées en erreur pour éviter une perte silencieuse de pages ou de tonalités. Les images trop petites pour un crop exact standard sont signalées ; No Crop accepte aussi les très petites images. Une erreur ne bloque pas le reste du batch. Les accents, le japonais et les espaces dans les chemins sont pris en charge.

La recherche et le traitement tournent dans un QThread. Attendre la fin avant de fermer l'application. Les chemins complets sont disponibles dans les info-bulles et copiables depuis le journal.

## Sauvegarde de la version initiale

Avant tout changement fonctionnel, les 9 tests initiaux ont été exécutés avec succès, puis le dépôt Git a été initialisé et le `.gitignore` complété.

- Commit initial : **`656aa11`** ; tag : **`v1.0-baseline`**.
- ZIP indépendant : **`backups/PhotoCrop4x3-v1.0-656aa11.zip`**, contenant les sources, tests, documentation, ancien EXE et versions exactes des dépendances. Git, environnements virtuels, dossiers de build et caches sont exclus.
- Le ZIP a été relu intégralement et ses fichiers comparés à un manifeste SHA-256 intégré.

Pour restaurer indépendamment : extraire le ZIP dans un autre dossier et lancer son `dist\PhotoCrop4x3.exe`, ou recréer l'environnement depuis `requirements-frozen.txt`.

Pour examiner l'ancienne version Git sans changer votre branche actuelle :

```powershell
git show v1.0-baseline:cropper/processing.py
git archive --format=zip --output=backups/source-v1-restored.zip v1.0-baseline
```

Pour travailler sur cette version, après avoir sauvegardé toute modification courante : `git switch -c restore-v1 v1.0-baseline`. Aucun reset destructif n'est nécessaire. L'archive Git ne contient pas l'EXE ; le ZIP de sauvegarde complet le contient.

## Lancer depuis les sources

Python **3.10 ou plus récent**, Windows x64 conseillé :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Tester et compiler

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name PhotoCropV2 main.py
```

Ou `powershell -ExecutionPolicy Bypass -File .\build.ps1`. Résultat : **`dist\PhotoCropV2.exe`**. Compiler sous Windows pour obtenir l'EXE Windows, non signé.

Contrôle facultatif du binaire compilé, sans interaction avec le bureau :

```powershell
Start-Process -FilePath .\dist\PhotoCropV2.exe -ArgumentList '--self-test', 'test-results\compiled-v2.json' -WindowStyle Hidden -Wait
Get-Content test-results\compiled-v2.json
```

Ce mode explicite crée des images synthétiques temporaires, pilote trois batches Qt, vérifie les JPEG et écrit un rapport JSON avec `passed: true` et `frozen: true`, ainsi qu'une capture PNG. Sans argument, l'application démarre normalement.

## Organisation

- `main.py` : lancement normal ou contrôle explicite de compilation.
- `cropper/gui.py` : interface, synchronisation des menus, worker et progression.
- `cropper/settings.py` : catalogue partagé et options immuables de traitement.
- `cropper/geometry.py` : calculs de crop et de dimensions de sortie.
- `cropper/discovery.py` : recherche, exclusions et dédoublonnage.
- `cropper/processing.py` : pipeline EXIF / crop / resize et erreurs individuelles.
- `cropper/export.py` : couleur, métadonnées et écriture JPEG exclusive.
- `cropper/smoke.py` : contrôle d'intégration du binaire autonome.
- `tests/` : tests sans dépendance de test supplémentaire.

Références : [resize Pillow](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.resize), [options JPEG](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#jpeg), [PyInstaller](https://pyinstaller.org/en/stable/usage.html).
