"""
Оптимизированный NLI движок на базе ruBERT-tiny (bilingual).
Реализует:
1. Дисковое кэширование результатов (data/cache/nli_cache.json).
2. Пакетную обработку (Batch Inference) для CPU.
3. Локальное хранение модели.
"""
import json
import os
import torch
import torch.nn.functional as F
from pathlib import Path
from typing import List, Dict, Tuple
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from tqdm import tqdm

MODEL_NAME = "cointegrated/rubert-tiny-bilingual-nli"
CACHE_FILE = Path("data/cache/nli_cache.json")

_tokenizer = None
_model = None

torch.set_num_threads(os.cpu_count() or 4)

def _get_nli():
    global _tokenizer, _model
    if _model is not None:
        return _tokenizer, _model
    
    os.environ["TRANSFORMERS_CACHE"] = str(Path("data/models").absolute())
    
    print(f"Загрузка легковесной NLI модели {MODEL_NAME}...")
    _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    _model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
    _model.eval()
    
    _model.to("cpu")
    
    return _tokenizer, _model

def load_cache() -> Dict:
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(cache: Dict):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def check_contradictions_batch(pairs: List[Tuple[str, str, str, str]], batch_size: int = 32) -> List[Dict]:
    """
    Пакетная проверка пар текстов на противоречие.
    pairs: Список кортежей (text_a, text_b, id_a, id_b)
    """
    if not pairs:
        return []

    tokenizer, model = _get_nli()
    cache = load_cache()
    results = []
    
    to_infer = []
    to_infer_indices = []
    
    for i, (text_a, text_b, id_a, id_b) in enumerate(pairs):
        cache_key = f"{id_a}_{id_b}"
        
        if cache_key in cache:
            results.append(cache[cache_key])
        else:
            to_infer.append((text_a, text_b))
            to_infer_indices.append(i)
            results.append(None)
            
    if not to_infer:
        return results

    print(f"NLI Inference: Обработка {len(to_infer)} новых пар...")
    
    processed_results = []
    for i in tqdm(range(0, len(to_infer), batch_size), desc="NLI Batch Processing"):
        batch_pairs = to_infer[i:i + batch_size]
        
        inputs = tokenizer(
            [p[0] for p in batch_pairs],
            [p[1] for p in batch_pairs],
            padding=True,
            truncation=True,
            max_length=320, # Снижаем для ускорения на CPU, 320 достаточно для большинства статей
            return_tensors="pt"
        )
        
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits
            probs = F.softmax(logits, dim=-1)
            
        id2label = model.config.id2label
        label_map = {v.lower(): k for k, v in id2label.items()}
        c_idx = label_map.get("contradiction", label_map.get("not_entailment", 1))
        e_idx = label_map.get("entailment", 0)
        
        batch_res = []
        for p in probs:
            p = p.cpu().numpy()
            entail = float(p[e_idx])
            contra = float(p[c_idx])
            
            if contra > entail and contra > 0.5:
                label = "contradiction"
                conf = contra
            elif entail > contra and entail > 0.5:
                label = "entailment"
                conf = entail
            else:
                label = "neutral"
                conf = float(max(p))
                
            batch_res.append({
                "label": label,
                "confidence": conf
            })
        
        processed_results.extend(batch_res)

        if (i // batch_size) % 100 == 0 and i > 0:
            temp_cache = cache.copy()
            for idx_in_infer_tmp, global_idx_tmp in enumerate(to_infer_indices[:len(processed_results)]):
                id_a_t, id_b_t = pairs[global_idx_tmp][2], pairs[global_idx_tmp][3]
                temp_cache[f"{id_a_t}_{id_b_t}"] = processed_results[idx_in_infer_tmp]
            save_cache(temp_cache)

    for idx_in_infer, global_idx in enumerate(to_infer_indices):
        res = processed_results[idx_in_infer]
        results[global_idx] = res
        id_a, id_b = pairs[global_idx][2], pairs[global_idx][3]
        cache[f"{id_a}_{id_b}"] = res
        
    save_cache(cache)
    return results

def check_contradiction(text_a: str, text_b: str) -> dict:
    """Для обратной совместимости с одиночными вызовами"""
    res = check_contradictions_batch([(text_a, text_b, "tmp_a", "tmp_b")], batch_size=1)
    return res[0]
