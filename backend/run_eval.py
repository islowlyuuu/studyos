"""跑评测：召回质量（Recall@K/MRR）与引用正确性/完整性。

用法：
  python run_eval.py                # 只跑检索召回评测
  python run_eval.py --citations    # 额外跑带引用问答（会调用 DeepSeek，产生少量费用）

前提：先导入学习资料到知识库，否则相关片段数为 0，指标全为 0。
"""
import argparse
import json
import os

from app.services.evaluation import evaluate_citations, evaluate_retrieval

EVAL_FILE = os.path.join(os.path.dirname(__file__), "eval", "eval_set.json")
DEFAULT_USER_ID = 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--citations", action="store_true", help="额外跑引用正确性/完整性评估")
    args = parser.parse_args()

    with open(EVAL_FILE, encoding="utf-8") as f:
        eval_set = json.load(f)
    print(f"评测集: {len(eval_set)} 题\n")

    print("=" * 60)
    print("检索召回评估 (Recall@K / MRR)")
    print("=" * 60)
    result = evaluate_retrieval(eval_set, DEFAULT_USER_ID)
    for row in result["rows"]:
        print(
            f"#{row['id']:>2} Recall@{row['k']}={row['recall_at_k']:.2f}  "
            f"MRR={row['mrr']:.2f}  相关片段={row['n_relevant']}  {row['question'][:24]}..."
        )
    print(f"\n平均 Recall@{result['rows'][0]['k'] if result['rows'] else '-'} = {result['avg_recall_at_k']:.3f}")
    print(f"平均 MRR = {result['avg_mrr']:.3f}")

    if args.citations:
        print("\n" + "=" * 60)
        print("带引用问答评估 (引用正确性 / 完整性)")
        print("=" * 60)
        cit = evaluate_citations(eval_set, DEFAULT_USER_ID)
        for row in cit["rows"]:
            print(
                f"#{row['id']:>2} 正确性={row['citation_correctness']:.2f}  "
                f"完整性={row['completeness']:.2f}  引用={row['cited']}  "
                f"缺要点={row['missing_key_points']}"
            )
        print(f"\n平均引用正确性 = {cit['avg_citation_correctness']:.3f}")
        print(f"平均完整性 = {cit['avg_completeness']:.3f}")


if __name__ == "__main__":
    main()
