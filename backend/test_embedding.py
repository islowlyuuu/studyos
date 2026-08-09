import numpy as np

from app.llm.embeddings import embed_texts

vecs = embed_texts(["Transformer 的自注意力机制是什么", "RAG 检索增强生成流程"])
print("向量数量:", len(vecs))
print("向量维度:", len(vecs[0]))
a = np.array(vecs[0])
b = np.array(vecs[1])
print("两句话的余弦相似度:", round(float(a @ b), 4))
