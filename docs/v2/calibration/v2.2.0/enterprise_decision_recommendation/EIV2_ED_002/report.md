# Enterprise Insight

pgvector 是 PostgreSQL 的开源扩展,用于在关系型数据库中存储、索引和检索向量。 [ev\_da115e732ec66537](<https://cloud.google.com/discover/what-is-pgvector?hl=zh-CN>) [ev\_c9d5eadb6fa50bc7](<https://cloud.google.com/discover/what-is-pgvector?hl=zh-CN>) [ev\_00b4876769cb1a7f](<https://intl.cloud.tencent.com/zh/document/product/409/80360>)

pgvector 支持精确和近似最近邻搜索,并支持 vector、halfvec、sparsevec 等向量类型。 [ev\_00b4876769cb1a7f](<https://intl.cloud.tencent.com/zh/document/product/409/80360>) [ev\_42ac6ab50515841f](<https://intl.cloud.tencent.com/zh/document/product/409/80360>)

pgvector 提供 HNSW 和 IVFFlat 索引,支持 L2 欧氏距离、余弦相似度、内积、L1 曼哈顿距离等距离度量。 [ev\_00b4876769cb1a7f](<https://intl.cloud.tencent.com/zh/document/product/409/80360>) [ev\_42ac6ab50515841f](<https://intl.cloud.tencent.com/zh/document/product/409/80360>) [ev\_1ef8b48068fe5e84](<https://developer.cloud.tencent.com/article/2658089>)

pgvector 可直接集成到现有 PostgreSQL 数据库,无需单独基础设施或迁移数据,也无需更改应用架构。 [ev\_da115e732ec66537](<https://cloud.google.com/discover/what-is-pgvector?hl=zh-CN>) [ev\_c9d5eadb6fa50bc7](<https://cloud.google.com/discover/what-is-pgvector?hl=zh-CN>)

Milvus 需要 Docker Compose 或 Kubernetes 部署;单机版也需要同时运行 etcd、MinIO 和 Milvus 三个容器;生产集群还需配置 Pulsar 或 Kafka。 [ev\_332ae8b15ef78f5f](<https://developer.cloud.tencent.com/article/2658089>)

pgvector 的备份可使用 pg\_dump,高可用可使用 repmgr 或 Patroni,全部复用 PostgreSQL 生态,不需要学习新工具。 [ev\_332ae8b15ef78f5f](<https://developer.cloud.tencent.com/article/2658089>)

从架构选型看,向量检索不再是单一选型决策,而需根据向量规模、查询模式、架构偏好选择不同方案。 [ev\_1f4a4d719a744227](<https://blog.csdn.net/afjkdajs/article/details/163944680>)

在 PolarDB PostgreSQL 版中,创建向量扩展、测试表、为 embedding 列创建 ivfflat 索引,并存储知识库内容,可用于企业专属 Chatbot。 [ev\_49d96459d8fbcd3d](<https://www.alibabacloud.com/help/zh/polardb/polardb-for-postgresql/build-enterprise-specific-chatbot-based-on-polardb-postgresql-and-llm>)
