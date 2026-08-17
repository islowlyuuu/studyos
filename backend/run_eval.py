"""运行 StudyOS 的概念评测或真实语料评测。

用法：
  python run_eval.py
  python run_eval.py --citations
  python run_eval.py --corpus eval/ai_corpus_eval.json
"""
import argparse
import json
import os

from app.services.evaluation import (
    evaluate_citations,
    evaluate_real_corpus,
    evaluate_retrieval,
    load_corpus_eval,
    validate_corpus_eval,
)

EVAL_FILE = os.path.join(os.path.dirname(__file__), "eval", "eval_set.json")
DEFAULT_USER_ID = 1


def _run_corpus(path: str, validate_only: bool) -> None:
    dataset = load_corpus_eval(path)
    validation = validate_corpus_eval(dataset, DEFAULT_USER_ID)
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    if validate_only:
        return
    report = evaluate_real_corpus(dataset, DEFAULT_USER_ID)
    print(json.dumps(report, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--citations", action="store_true", help="额外跑引用正确性/完整性评估")
    parser.add_argument("--corpus", help="真实语料评测集 JSON 路径")
    parser.add_argument("--validate-only", action="store_true", help="只校验真实语料评测集")
    args = parser.parse_args()

    if args.corpus:
        _run_corpus(args.corpus, args.validate_only)
        return

    with open(EVAL_FILE, encoding="utf-8") as handle:
        eval_set = json.load(handle)
    result = evaluate_retrieval(eval_set, DEFAULT_USER_ID)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.citations:
        print(json.dumps(evaluate_citations(eval_set, DEFAULT_USER_ID), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
