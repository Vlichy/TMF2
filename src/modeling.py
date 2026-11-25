"""Experimento retrospectivo reproducible sobre reservas_historicas."""
from pathlib import Path
import hashlib
import json
import platform

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score, confusion_matrix, f1_score,
    precision_score, recall_score, roc_auc_score,
)
from sklearn.pipeline import Pipeline

from src.features import separate_model_data
from src.preparation import run_preparation
from src.preprocessing import build_preprocessor


def rank_quota(metadata, hotels, scores):
    """Selecciona el 20% por mes y hotel con desempate determinista."""
    ranking = pd.DataFrame({
        "mes": pd.to_datetime(metadata.meta_arrival_date).dt.strftime("%Y-%m"),
        "hotel": hotels,
        "score": scores,
        "id": metadata.meta_row_id,
    })
    ranking["desempate"] = ranking["id"].map(
        lambda row_id: hashlib.sha256(f"42|{row_id}".encode()).hexdigest()
    )
    selected = pd.Series(False, index=ranking.index)
    for _, group in ranking.groupby(["mes", "hotel"], sort=True):
        ordered = group.sort_values(
            ["score", "desempate", "id"], ascending=[False, True, True]
        )
        selected.loc[ordered.index[:len(group) * 20 // 100]] = True
    return selected


def evaluate(target, scores, selected, probability):
    """Métricas de ranking y del cupo común a modelo y regla."""
    result = {
        "roc_auc": float(roc_auc_score(target, scores)),
        "average_precision": float(average_precision_score(target, scores)),
        "cupo": int(selected.sum()),
        "positivos_detectados": int(target.loc[selected].sum()),
        "precision_cupo": float(precision_score(target, selected, zero_division=0)),
        "recall_cupo": float(recall_score(target, selected, zero_division=0)),
    }
    if probability:
        labels = np.asarray(scores) >= 0.5
        result["umbral_05"] = {
            "precision": float(precision_score(target, labels, zero_division=0)),
            "recall": float(recall_score(target, labels, zero_division=0)),
            "f1": float(f1_score(target, labels, zero_division=0)),
            "matriz_tn_fp_fn_tp": confusion_matrix(target, labels, labels=[0, 1]).ravel().tolist(),
        }
    return result


def run_modeling(project_root=None):
    root = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
    preparation = run_preparation(root)
    data = pd.read_csv(root / preparation["archivo_preparado"])
    features, target, metadata = separate_model_data(data)
    arrival = pd.to_datetime(metadata.meta_arrival_date)
    closed = pd.to_datetime(metadata.meta_label_available_after)
    partition = pd.Series("prueba", index=data.index)
    partition.loc[arrival < "2017-01-01"] = "validacion"
    partition.loc[arrival < "2016-07-01"] = "entrenamiento"
    group_partitions = partition.groupby(metadata.meta_duplicate_group).nunique()
    crossing = metadata.meta_duplicate_group.isin(group_partitions[group_partitions > 1].index)
    immature = (
        ((partition == "entrenamiento") & (closed >= "2016-07-01"))
        | ((partition == "validacion") & (closed >= "2017-01-01"))
    )
    partition.loc[immature] = "apartada_cierre"
    partition.loc[crossing] = "apartada_grupo"
    names = ["entrenamiento", "validacion", "prueba"]
    group_sets = [
        set(metadata.loc[partition == name, "meta_duplicate_group"]) for name in names
    ]
    assert all(group_sets[i].isdisjoint(group_sets[j]) for i in range(3) for j in range(i))
    assert closed.loc[partition == "entrenamiento"].lt(pd.Timestamp("2016-07-01")).all()
    assert closed.loc[partition == "validacion"].lt(pd.Timestamp("2017-01-01")).all()
    train = partition == "entrenamiento"
    validation = partition == "validacion"
    test = partition == "prueba"
    estimators = {
        "logistica": LogisticRegression(C=1, max_iter=2000, random_state=42),
        "bosque": RandomForestClassifier(
            n_estimators=150, max_depth=12, min_samples_leaf=20,
            random_state=42, n_jobs=2,
        ),
    }
    validation_results = {}
    fitted = {}
    for name, estimator in estimators.items():
        model = Pipeline([
            ("preparacion", build_preprocessor(scale_numeric=name == "logistica")),
            ("modelo", estimator),
        ])
        model.fit(features.loc[train], target.loc[train])
        scores = model.predict_proba(features.loc[validation])[:, 1]
        selected = rank_quota(metadata.loc[validation], features.loc[validation, "hotel"], scores)
        validation_results[name] = evaluate(target.loc[validation], scores, selected, True)
        fitted[name] = model
    winner = max(estimators, key=lambda name: validation_results[name]["average_precision"])
    for mask, results in [(validation, validation_results)]:
        scores = features.loc[mask, "lead_time"].to_numpy()
        selected = rank_quota(metadata.loc[mask], features.loc[mask, "hotel"], scores)
        results["regla_antelacion"] = evaluate(target.loc[mask], scores, selected, False)
    test_results = {}
    prediction_table = metadata.loc[test, ["meta_row_id", "meta_arrival_date"]].copy()
    prediction_table["hotel"] = features.loc[test, "hotel"]
    prediction_table["etiqueta"] = target.loc[test]
    for name, scores in [
        (winner, fitted[winner].predict_proba(features.loc[test])[:, 1]),
        ("regla_antelacion", features.loc[test, "lead_time"].to_numpy()),
    ]:
        selected = rank_quota(metadata.loc[test], features.loc[test, "hotel"], scores)
        test_results[name] = evaluate(target.loc[test], scores, selected, name == winner)
        prediction_table[f"score_{name}"] = scores
        prediction_table[f"seleccion_{name}"] = selected
    assert test_results[winner]["cupo"] == test_results["regla_antelacion"]["cupo"]
    blocks = {}
    for name in names:
        mask = partition == name
        blocks[name] = {
            "filas": int(mask.sum()), "positivos": int(target.loc[mask].sum()),
            "prevalencia": float(target.loc[mask].mean()),
            "llegada_min": str(arrival.loc[mask].min().date()),
            "llegada_max": str(arrival.loc[mask].max().date()),
        }
    result = {
        "tabla": "reservas_historicas",
        "objetivo": "is_canceled: cancelación o no presentación",
        "sha256_raw": preparation["sha256_original"],
        "sha256_gold": preparation["sha256_preparado"],
        "semilla": 42, "cupo_porcentaje": 20,
        "bloques": blocks, "apartadas_grupo": int(crossing.sum()),
        "apartadas_cierre": int((immature & ~crossing).sum()),
        "ganador": winner, "validacion": validation_results, "prueba": test_results,
        "versiones": {"python": platform.python_version(), "sklearn": sklearn.__version__,
                      "pandas": pd.__version__, "numpy": np.__version__},
    }
    reports = root / "reports"
    (reports / "modelo_historico_resultados.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    monthly = []
    for (month, hotel), group in prediction_table.groupby(
        [prediction_table.meta_arrival_date.str[:7], "hotel"]
    ):
        row = {"mes": month, "hotel": hotel, "filas": len(group),
               "positivos": int(group.etiqueta.sum())}
        for name in test_results:
            selected = group[f"seleccion_{name}"]
            row[f"cupo_{name}"] = int(selected.sum())
            row[f"detectados_{name}"] = int(group.loc[selected, "etiqueta"].sum())
        monthly.append(row)
    pd.DataFrame(monthly).to_csv(reports / "modelo_historico_mensual.csv", index=False)
    # Las predicciones y particiones completas quedan locales para auditoría.
    local = root / "data/processed"
    prediction_table.to_csv(local / "modelo_historico_predicciones.csv", index=False)
    metadata.assign(particion=partition).to_csv(local / "modelo_historico_particiones.csv", index=False)
    return result


if __name__ == "__main__":
    print(json.dumps(run_modeling(), ensure_ascii=False, indent=2))
