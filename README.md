# Flask Project (Python 3.10)

Projet Flask minimal, compatible avec Python 3.10.

## Prerequis

- Python 3.10.x
- pip

## Installation

```bash
python -m venv .venv
```

### Windows (PowerShell)

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Linux/macOS

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Lancer l'application

```bash
python run.py
```

L'application demarre sur `http://localhost:5000`.

## Endpoints disponibles

- `GET /` : interface formulaire Tailwind + JS reactif.
- `GET /health` : JSON de verification.
- `POST /api/predict` : simulation d'inference (tableau de reponses statique).

### Exemple de payload `POST /api/predict`

```json
{
	"N": 10,
	"P": 24,
	"H": 7.2,
	"Tep": 18,
	"GH": 4,
	"PO": 2
}
```
