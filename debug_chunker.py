"""
语义分块调试脚本

详细显示每个句子的评分、决策过程和最终结果
"""

import sys
sys.path.insert(0, 'preprocess')

from semantic_blocker import SemanticChunker, ChunkerConfig, GranularityMode, OllamaBackend
from sentence_splitter import SentenceSplitter
import logging

# 配置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 测试文本
text = """Mikel Arteta's Arsenal side marched on to the EFL Cup semi-finals but did it the hard way by winning 8-7 on penalties against Crystal Palace, with Kepa Arrizabalaga saving the 16th spot-kick taken by Maxence Lacroix after 15 successful conversions. Two late goals had resulted in a 1-1 draw after 90 minutes and a lengthy period of stoppage time. The Gunners will now face rivals Chelsea to fight for a place in the final at Wembley, with the first leg of their semi-final set for Stamford Bridge on 14 January.

After bossing much of the quarter-final against Palace and creating the majority of big chances, Arteta's men finally found their breakthrough, which came from a corner in the 80th minute. A well-placed delivery into the box from Bukayo Saka found the head of Riccardo Calafiori and eventually went into the net off Palace centre-back Lacroix. The unfortunate own goal did not dampen Palace's spirits as they went in search of an equaliser. When it finally did arrive, they had club captain Marc Guehi to thank. The England international was the first to react to a knock-on from Jefferson Lerma in the fifth minute of stoppage time.

A fascinating penalty shoot-out then ensued, with both sides delivering spectacular finishes to take the score to 8-7. When the own-goal scorer Lacroix stepped up to take his kick, Arsenal keeper Kepa read its direction and made the save to ensure the Gunners remain on course for their first Wembley appearance in five years.

This was Arsenal's second-highest scoring penalty shootout, after their 9-8 victory against Rotherham in 2003/04. Overall, the Gunners have converted 47 of their last 51 spot-kicks in shoot-outs, giving them a supreme 92 per cent conversion rate.

Arteta told Sky Sports after the game: "I'm very happy to be in the semi-finals. We played against a team who are hard to generate chances against. We generated a lot and we should have scored many more goals." The Arsenal boss had made eight changes to his starting line-up and admitted: "It's always tough because they don't have the right chemistry when they haven't played together. But their attitude is excellent. "I think we had some big individual performances tonight. It's great for Gabriel Jesus tonight, after almost a year out, to start a game and make his 100th [Arsenal] appearance. The commitment within the group is incredible and I'm very happy for the boys."
"""


def debug_chunking(granularity=GranularityMode.MEDIUM):
    """详细调试分块过程"""
    
    print("="*80)
    print(f"调试模式: {granularity.value.upper()} 粒度")
    print("="*80)
    
    # 1. 分句
    print("\n[步骤 1] 分句...")
    splitter = SentenceSplitter()
    sentences = splitter.split(text)
    print(f"共分出 {len(sentences)} 个句子\n")
    
    for i, sent in enumerate(sentences, 1):
        preview = sent[:70] + "..." if len(sent) > 70 else sent
        print(f"  [{i:2d}] {preview}")
    
    # 2. 配置 chunker（启用详细日志）
    print("\n[步骤 2] 配置语义分块器...")
    backend = OllamaBackend(model="llama3:latest", temperature=0.2)
    config = ChunkerConfig(
        granularity=granularity,
        context_window=2,
        max_sentences_per_chunk=5,
        enable_structural_rules=True,
        enable_orphan_merge=True,
        log_scores=True  # 启用评分日志
    )
    
    print(f"  - 粒度: {config.granularity.value}")
    print(f"  - 阈值: {config.break_threshold}")
    print(f"  - 上下文窗口: {config.context_window}")
    print(f"  - 最大句数/块: {config.max_sentences_per_chunk}")
    
    chunker = SemanticChunker(llm=backend, config=config)
    
    # 3. 执行分块
    print("\n[步骤 3] 执行语义分块...")
    print("-"*80)
    chunks = chunker.chunk(sentences)
    print("-"*80)
    
    # 4. 显示结果
    print(f"\n[步骤 4] 分块结果: {len(chunks)} 个块\n")
    
    for chunk in chunks:
        print(f"{'='*80}")
        print(f"块 {chunk.chunk_id} | 类型: {chunk.chunk_type} | 句数: {len(chunk)}")
        print(f"{'='*80}")
        
        for i, sent in enumerate(chunk.sentences, 1):
            # 显示句子
            preview = sent[:100] + "..." if len(sent) > 100 else sent
            print(f"  [{i}] {preview}")
            
            # 显示对应的评分（除了第一句）
            if i > 1 and chunk.scores and len(chunk.scores) >= i - 1:
                score = chunk.scores[i - 2]
                print(f"      └─ 评分: {score:.2f} (阈值: {config.break_threshold})")
        
        print()
    
    # 5. 统计信息
    print("\n[步骤 5] 详细统计")
    print("="*80)
    stats = chunker.get_stats()
    
    print(f"总LLM调用次数: {stats['total_scores']}")
    print(f"LLM失败次数: {stats['llm_failures']}")
    print(f"强制分割(大小限制): {stats['forced_splits_size']}")
    print(f"强制分割(结构化规则): {stats['forced_splits_structural']}")
    print(f"孤立块合并: {stats['orphan_merges']}")
    
    if stats['score_distribution']:
        print(f"\n评分统计:")
        print(f"  - 平均: {stats.get('avg_score', 0):.2f}")
        print(f"  - 最小: {stats.get('min_score', 0):.2f}")
        print(f"  - 最大: {stats.get('max_score', 0):.2f}")
        print(f"  - 所有评分: {[f'{s:.2f}' for s in stats['score_distribution']]}")
    
    # 6. 分析
    print("\n[步骤 6] 分块分析")
    print("="*80)
    
    total_sentences = sum(len(chunk) for chunk in chunks)
    avg_sentences_per_chunk = total_sentences / len(chunks) if chunks else 0
    
    print(f"总句数: {total_sentences}")
    print(f"总块数: {len(chunks)}")
    print(f"平均句数/块: {avg_sentences_per_chunk:.1f}")
    print(f"压缩率: {len(chunks)/total_sentences*100:.1f}%")
    
    print("\n块大小分布:")
    size_dist = {}
    for chunk in chunks:
        size = len(chunk)
        size_dist[size] = size_dist.get(size, 0) + 1
    
    for size in sorted(size_dist.keys()):
        count = size_dist[size]
        bar = "█" * count
        print(f"  {size:2d} 句: {bar} ({count} 个块)")
    
    print("\n块类型分布:")
    type_dist = {}
    for chunk in chunks:
        chunk_type = chunk.chunk_type
        type_dist[chunk_type] = type_dist.get(chunk_type, 0) + 1
    
    for chunk_type in sorted(type_dist.keys()):
        count = type_dist[chunk_type]
        print(f"  {chunk_type:20s}: {count} 个块")
    
    return chunks, stats


def compare_granularities():
    """对比不同粒度的效果"""
    print("\n" + "="*80)
    print("对比不同粒度模式")
    print("="*80 + "\n")
    
    results = {}
    
    for mode in [GranularityMode.FINE, GranularityMode.MEDIUM, GranularityMode.COARSE]:
        print(f"\n{'#'*80}")
        print(f"# 测试粒度: {mode.value.upper()}")
        print(f"{'#'*80}\n")
        
        chunks, stats = debug_chunking(mode)
        results[mode.value] = {
            'chunks': len(chunks),
            'avg_score': stats.get('avg_score', 0),
            'forced_structural': stats['forced_splits_structural']
        }
        
        input("\n按回车继续下一个粒度测试...")
    
    # 总结对比
    print("\n" + "="*80)
    print("粒度对比总结")
    print("="*80)
    print(f"{'粒度':<10} {'块数':<8} {'平均分':<10} {'结构化切分'}")
    print("-"*80)
    for mode_name, result in results.items():
        print(f"{mode_name:<10} {result['chunks']:<8} {result['avg_score']:<10.2f} {result['forced_structural']}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='语义分块调试工具')
    parser.add_argument(
        '--granularity', '-g',
        choices=['fine', 'medium', 'coarse'],
        default='medium',
        help='粒度模式 (默认: medium)'
    )
    parser.add_argument(
        '--compare', '-c',
        action='store_true',
        help='对比所有粒度模式'
    )
    
    args = parser.parse_args()
    
    if args.compare:
        compare_granularities()
    else:
        granularity_map = {
            'fine': GranularityMode.FINE,
            'medium': GranularityMode.MEDIUM,
            'coarse': GranularityMode.COARSE
        }
        debug_chunking(granularity_map[args.granularity])
