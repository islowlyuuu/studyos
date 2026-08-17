import unittest

from app.services.evaluation import mrr, recall_at_k


class MetricTests(unittest.TestCase):
    def test_recall_and_mrr_use_gold_chunk_ids(self):
        self.assertEqual(recall_at_k([4, 2, 3], {2, 3}, 2), 0.5)
        self.assertEqual(mrr([4, 2, 3], {2, 3}), 0.5)

    def test_empty_gold_labels_are_zero(self):
        self.assertEqual(recall_at_k([1], set(), 1), 0.0)
        self.assertEqual(mrr([1], set()), 0.0)


if __name__ == "__main__":
    unittest.main()
