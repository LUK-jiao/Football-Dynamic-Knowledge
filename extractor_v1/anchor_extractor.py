"""
Anchor Extractor - Business Layer

业务调用层，直接调用 ollama_backend，不做任何规则、推理、字段修改。
"""

import time
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from extractor_v1.ollama_backend import OllamaBackend


class AnchorExtractor:
    """
    事实锚点抽取器（Business Layer）
    
    职责：
    1. 调用 ollama_backend 进行抽取
    2. 验证输入格式
    3. 不引入 NLP 规则、不做正则、不做 spaCy
    4. 直接透传 backend 输出，不做任何修改
    """
    
    def __init__(
        self,
        model: str = "llama3:latest",
        host: str = "http://localhost:11434"
    ):
        """
        初始化抽取器
        
        Args:
            model: Ollama 模型名称
            host: Ollama 服务地址
        """
        self.backend = OllamaBackend(model=model, host=host)
    
    def extract_anchors(self, block: Dict[str, Any]) -> Dict[str, Any]:
        """
        从单个语义块中抽取锚点
        
        Args:
            block: 输入的语义块，必须包含：
                - block_id: 唯一标识
                - text: 原始文本
                - source: 信息来源
                - publish_date: 发布日期
        
        Returns:
            包含锚点的结果 dict，结构：
            {
                "block_id": "...",
                "text": "...",
                "source": "...",
                "publish_date": "...",
                "anchors": {
                    "participants": [...],
                    "temporal_anchors": [...],
                    "sources": [...],
                    "constraints": [...]
                },
                "fact_type": "EVENT|STATE",
                "need_resolver": true|false,
                "inference_time": 1.234  # LLM 推理时间（秒）
            }
        
        Raises:
            ValueError: 输入格式不正确
        """
        # 验证输入
        self._validate_input(block)
        
        # 记录开始时间
        start_time = time.time()
        
        # 调用 backend（直接透传，不做任何修改）
        result = self.backend.extract_anchors(block)
        
        # 记录结束时间并计算推理时间
        end_time = time.time()
        inference_time = end_time - start_time
        
        # 添加推理时间到结果中
        result['inference_time'] = round(inference_time, 3)
        
        return result
    
    def extract_anchors_batch(
        self, 
        blocks: List[Dict[str, Any]], 
        max_workers: int = 4,
        show_progress: bool = True
    ) -> List[Dict[str, Any]]:
        """
        批量抽取（并发处理）
        
        Args:
            blocks: 语义块列表
            max_workers: 最大并发线程数（默认4，可根据CPU核心数调整）
            show_progress: 是否显示进度
        
        Returns:
            结果列表（顺序与输入一致）
            
        注意：
            - 使用 ThreadPoolExecutor 并发调用 Ollama
            - Ollama 本身是多线程安全的
            - 可以显著减少总处理时间
        """
        results = [None] * len(blocks)  # 预分配结果数组
        total = len(blocks)
        completed = 0
        
        if show_progress:
            print(f"🚀 开始并发处理 {total} 个 blocks（并发数: {max_workers}）...")
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务，保存 future -> (index, block) 映射
            future_to_index = {
                executor.submit(self._extract_single_safe, block): (idx, block)
                for idx, block in enumerate(blocks)
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_index):
                idx, block = future_to_index[future]
                completed += 1
                
                try:
                    result = future.result()
                    results[idx] = result
                    
                    if show_progress:
                        block_id = block.get('block_id', 'unknown')
                        inference_time = result.get('inference_time', 0)
                        print(f"✅ [{completed}/{total}] {block_id} 完成 (耗时: {inference_time:.2f}s)")
                        
                except Exception as e:
                    block_id = block.get('block_id', 'unknown')
                    error_result = {
                        "block_id": block_id,
                        "error": str(e)
                    }
                    results[idx] = error_result
                    
                    if show_progress:
                        print(f"❌ [{completed}/{total}] {block_id} 失败: {str(e)}")
        
        total_time = time.time() - start_time
        
        if show_progress:
            avg_time = total_time / total if total > 0 else 0
            print(f"\n✅ 批量处理完成！")
            print(f"   总耗时: {total_time:.2f}s")
            print(f"   平均耗时: {avg_time:.2f}s/block")
            print(f"   加速比: ~{len(blocks) * 8 / total_time:.1f}x（相比顺序处理）")
        
        return results
    
    def _extract_single_safe(self, block: Dict[str, Any]) -> Dict[str, Any]:
        """
        安全地抽取单个 block（用于并发调用）
        
        Args:
            block: 语义块
            
        Returns:
            抽取结果
        """
        try:
            return self.extract_anchors(block)
        except Exception as e:
            return {
                "block_id": block.get("block_id", "unknown"),
                "error": str(e)
            }
    
    def _validate_input(self, block: Dict[str, Any]):
        """
        验证输入格式
        
        Args:
            block: 输入的语义块
        
        Raises:
            ValueError: 输入格式不正确
        """
        required_fields = ["block_id", "text", "source", "publish_date"]
        
        for field in required_fields:
            if field not in block:
                raise ValueError(f"输入缺少必需字段: {field}")
        
        if not block["text"] or not block["text"].strip():
            raise ValueError("text 字段不能为空")


# ============================================================================
# 便捷函数
# ============================================================================

def extract_anchors_from_block(
    block: Dict[str, Any],
    model: str = "llama3.2:latest"
) -> Dict[str, Any]:
    """
    从单个 block 抽取锚点（便捷函数）
    
    Args:
        block: 输入的语义块
        model: Ollama 模型名称
    
    Returns:
        包含锚点的结果 dict
    """
    extractor = AnchorExtractor(model=model)
    return extractor.extract_anchors(block)


# ============================================================================
# 测试入口
# ============================================================================

if __name__ == "__main__":
    import json
    
    print("=" * 100)
    print("测试 AnchorExtractor")
    print("=" * 100)
    print()
    
    # 初始化抽取器
    extractor = AnchorExtractor(model="llama3.2:latest")
    
    # 测试场景 1：转会新闻（EVENT）
    print("📋 测试 1: 转会新闻（EVENT）")
    print("-" * 100)
    
    block1 = {
        "block_id": "test_001",
        "text": "Matthijs de Ligt completes €50m move from Bayern Munich to Manchester United. The 25-year-old defender signs a five-year deal until June 2029.",
        "source": "BBC Sport",
        "publish_date": "2024-07-30"
    }
    
    try:
        result1 = extractor.extract_anchors(block1)
        print("✅ 抽取成功")
        print(json.dumps(result1, indent=2, ensure_ascii=False))
        print()
        print(f"Fact Type: {result1.get('fact_type')}")
        print(f"Need Resolver: {result1.get('need_resolver')}")
    except Exception as e:
        print(f"❌ 抽取失败: {str(e)}")
    
    print()
    
    # 测试场景 2：教练身份（STATE）
    print("=" * 100)
    print("📋 测试 2: 教练身份（STATE）")
    print("-" * 100)
    
    block2 = {
        "block_id": "test_002",
        "text": "Ruben Amorim is the head coach of Manchester United.",
        "source": "Official",
        "publish_date": "2025-01-15"
    }
    
    try:
        result2 = extractor.extract_anchors(block2)
        print("✅ 抽取成功")
        print(json.dumps(result2, indent=2, ensure_ascii=False))
        print()
        print(f"Fact Type: {result2.get('fact_type')}")
        print(f"Need Resolver: {result2.get('need_resolver')}")
    except Exception as e:
        print(f"❌ 抽取失败: {str(e)}")
    
    print()
    
    # 测试场景 3：合同状态（STATE，有 valid_to）
    print("=" * 100)
    print("📋 测试 3: 合同状态（STATE，有 valid_to）")
    print("-" * 100)
    
    block3 = {
        "block_id": "test_003",
        "text": "De Ligt signed a contract with Manchester United until 2028.",
        "source": "ESPN",
        "publish_date": "2024-07-30"
    }
    
    try:
        result3 = extractor.extract_anchors(block3)
        print("✅ 抽取成功")
        print(json.dumps(result3, indent=2, ensure_ascii=False))
        print()
        print(f"Fact Type: {result3.get('fact_type')}")
        print(f"Need Resolver: {result3.get('need_resolver')}")
    except Exception as e:
        print(f"❌ 抽取失败: {str(e)}")
    
    print()
    
    # 测试批量处理
    print("=" * 100)
    print("📋 测试 4: 批量处理")
    print("-" * 100)
    
    blocks = [block1, block2, block3]
    
    try:
        results = extractor.extract_anchors_batch(blocks)
        print(f"✅ 批量抽取完成，处理 {len(results)} 个 blocks")
        
        for i, result in enumerate(results, 1):
            if "error" in result:
                print(f"Block {i}: ❌ {result['error']}")
            else:
                print(f"Block {i}: ✅ {result.get('fact_type')} (need_resolver={result.get('need_resolver')})")
    except Exception as e:
        print(f"❌ 批量抽取失败: {str(e)}")
