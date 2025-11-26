# Football Dynamic Knowledge - 动态大模型知识库系统

一个面向足球爱好者的智能知识库系统，集成了数据爬取、知识图谱、向量检索和 RAG（检索增强生成）等功能。

## 项目概述

本项目旨在构建一个动态更新的足球知识库，通过爬取多源数据、提取结构化信息、构建知识图谱，并结合大语言模型提供智能问答服务。

### 核心功能

- **数据采集**：多协议爬虫支持（Web、API、RSS），定时调度
- **预处理**：文本清洗、分句、语言检测
- **信息抽取**：NER、关系抽取、事件抽取
- **知识图谱**：基于 Neo4j 的图数据库存储
- **向量检索**：支持密集向量、稀疏向量和混合检索
- **RAG 问答**：检索增强生成，提供准确的足球知识问答
- **多源验证**：NLI 自然语言推理验证
- **用户反馈**：支持用户标注和反馈收集

## 技术栈

- **Web 框架**: FastAPI
- **异步任务**: Celery + Redis
- **数据库**: PostgreSQL, Neo4j
- **向量存储**: Qdrant / Milvus（可选）
- **LLM**: OpenAI GPT-4
- **Embedding**: OpenAI text-embedding-3-small
- **其他**: BeautifulSoup, sentence-transformers, LangChain

## 项目结构

