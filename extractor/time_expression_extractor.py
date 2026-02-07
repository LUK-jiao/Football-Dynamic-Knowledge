"""
时间表达式提取器

从文本中提取各类时间表达式，包括：
- DAY: 完整日期
- MONTH: 年月
- YEAR: 年份
- DURATION: 时间段
- RELATIVE: 相对时间
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class TimeGranularity(str, Enum):
    """时间粒度枚举"""
    YEAR = "YEAR"           # 年份：2021
    MONTH = "MONTH"         # 年月：2021-09
    DAY = "DAY"             # 完整日期：2021-09-01
    DURATION = "DURATION"   # 时间段：four-and-a-half year
    RELATIVE = "RELATIVE"   # 相对时间：last year, yesterday, 2 years ago


class TimeExpressionExtractor:
    """时间表达式提取器"""
    
    def __init__(self):
        pass
    
    def extract_time_expressions(self, text: str, publish_date: str) -> List[Dict[str, Any]]:
        """
        提取时间表达式（职责缩减版）
        
        职责：仅识别文本中的时间表达，不判定其与事件的对应关系
        
        Args:
            text: 输入文本
            publish_date: 发布日期（用于补全缺失的年份）
        
        Returns:
            [{
                "time_id": "T1",
                "evidence": "...",
                "normalized": "...",
                "granularity": "YEAR/MONTH/DAY/DURATION/RELATIVE",
                "span": (start, end)
            }, ...]
        """
        time_expressions = []
        time_id_counter = 1
        seen_spans = set()  # 基于 span 去重
        normalized_values = {}  # 用于去重：normalized -> (优先级, span, 表达式)
        
        # 1. 完整日期（1 September 2025, September 1, 2025, 2025-09-01）
        date_patterns = [
            (r'\b(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b', 'dmy'),
            (r'\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b', 'mdy'),
            (r'\b(\d{4}-\d{2}-\d{2})\b', 'iso'),
        ]
        for pattern, fmt in date_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                span = (match.start(), match.end())
                if span in seen_spans:
                    continue
                evidence = match.group(1).strip()
                normalized = self._normalize_date(evidence)
                if normalized:
                    # 优先级：完整格式 > 其他格式（根据 span 长度判断）
                    priority = len(evidence)
                    
                    # 检查是否有相同的 normalized 值
                    if normalized in normalized_values:
                        existing_priority, existing_span, _ = normalized_values[normalized]
                        # 保留优先级更高（更完整）的表达式
                        if priority <= existing_priority:
                            continue
                        else:
                            # 移除旧的 span
                            seen_spans.discard(existing_span)
                    
                    time_expressions.append({
                        "time_id": f"T{time_id_counter}",
                        "evidence": evidence,
                        "normalized": normalized,
                        "granularity": TimeGranularity.DAY,
                        "span": span
                    })
                    seen_spans.add(span)
                    normalized_values[normalized] = (priority, span, evidence)
                    time_id_counter += 1
        
        # 1.5 日期+月份（无年份）（on 14 January, 14 January）
        # 使用 publish_date 的年份来补全
        day_month_pattern = r'\b(?:on\s+)?(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December))\b'
        for match in re.finditer(day_month_pattern, text, re.IGNORECASE):
            span = (match.start(), match.end())
            if span in seen_spans:
                continue
            evidence = match.group(0).strip()
            day_month = match.group(1).strip()
            
            # 从 publish_date 提取年份（假设 publish_date 格式为 YYYY-MM-DD）
            try:
                pub_year = publish_date[:4] if publish_date and len(publish_date) >= 4 else "2025"
                # 构建完整日期字符串
                full_date_str = f"{day_month} {pub_year}"
                normalized = self._normalize_date(full_date_str)
                if normalized:
                    # 检查是否与已有的完整日期重复
                    if normalized in normalized_values:
                        existing_priority, _, _ = normalized_values[normalized]
                        # 如果已有更完整的表达式，跳过
                        if existing_priority > len(evidence):
                            continue
                    
                    time_expressions.append({
                        "time_id": f"T{time_id_counter}",
                        "evidence": evidence,
                        "normalized": normalized,
                        "granularity": TimeGranularity.DAY,
                        "span": span
                    })
                    seen_spans.add(span)
                    normalized_values[normalized] = (len(evidence), span, evidence)
                    time_id_counter += 1
            except Exception:
                # 如果处理失败，跳过这个匹配
                pass
        
        # 2. 年月（in September 2025, during March 2023, June 2029, until March 2024）
        month_year_patterns = [
            # 带介词的形式
            r'\b(?:in|during|until|by)\s+((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b',
            # 不带介词的形式（独立的月份+年份）
            r'\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b',
        ]
        
        for pattern in month_year_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                span = (match.start(), match.end())
                if span in seen_spans:
                    continue
                evidence = match.group(0).strip()
                month_year = match.group(1)
                normalized = self._normalize_date(month_year + " 01")
                if normalized:
                    year_month = normalized[:7]  # YYYY-MM
                    
                    # 检查重复
                    if year_month in normalized_values:
                        existing_priority, _, _ = normalized_values[year_month]
                        if len(evidence) <= existing_priority:
                            continue
                    
                    time_expressions.append({
                        "time_id": f"T{time_id_counter}",
                        "evidence": evidence,
                        "normalized": year_month,
                        "granularity": TimeGranularity.MONTH,
                        "span": span
                    })
                    seen_spans.add(span)
                    normalized_values[year_month] = (len(evidence), span, evidence)
                    time_id_counter += 1
        
        # 3. 年份（in 2021, during 2023, the 2021 season, in 2003/04）
        year_patterns = [
            (r'\bin\s+(\d{4})/\d{2}\b', 'cross_year'),  # in 2003/04
            (r'\bin\s+(\d{4})\b', 'simple'),
            (r'\bduring\s+(\d{4})\b', 'simple'),
            (r'\bthe\s+(\d{4})\s+season\b', 'simple'),
            (r'\b(\d{4})/\d{2}\s+season\b', 'simple'),
        ]
        
        # 辅助函数：检查 span 是否被已有的 year 覆盖
        def _is_covered_by_year(span, year_data):
            """检查 span 是否被已有 year 完全覆盖或覆盖其他 year"""
            for year_val, (s, e) in year_data.items():
                # 如果被完全覆盖
                if s <= span[0] and span[1] <= e:
                    return True
                # 如果覆盖其他 year（自己更大），且年份相同，则优先保留更长的
                if span[0] <= s and e <= span[1]:
                    return True
            return False
        
        year_data = {}  # 记录已识别的 year: (span_start, span_end)
        
        for pattern, fmt in year_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                span = (match.start(), match.end())
                if span in seen_spans:
                    continue
                    
                evidence = match.group(0).strip()
                year = match.group(1)
                
                # 检查是否与已有的 year span 有覆盖关系
                if _is_covered_by_year(span, year_data):
                    continue
                
                # 检查相同 normalized 年份
                if year in normalized_values:
                    existing_priority, existing_span, _ = normalized_values[year]
                    # 保留更详细的表达式
                    if len(evidence) <= existing_priority:
                        continue
                    else:
                        # 移除旧的
                        seen_spans.discard(existing_span)
                        if year in year_data:
                            del year_data[year]
                    
                time_expressions.append({
                    "time_id": f"T{time_id_counter}",
                    "evidence": evidence,
                    "normalized": year,
                    "granularity": TimeGranularity.YEAR,
                    "span": span
                })
                seen_spans.add(span)
                year_data[year] = span
                normalized_values[year] = (len(evidence), span, evidence)
                time_id_counter += 1
        
        # 4. 相对时间（RELATIVE）
        # 4.1 方向型：last/next/this + 时间单位
        relative_direction_patterns = [
            (r'\b(last\s+(?:year|season|month|week|summer|winter))\b', lambda m: m.group(1).upper().replace(' ', '_')),
            (r'\b(next\s+(?:year|season|month|week|summer|winter))\b', lambda m: m.group(1).upper().replace(' ', '_')),
            (r'\b(this\s+(?:year|season|month|week|summer|winter))\b', lambda m: m.group(1).upper().replace(' ', '_')),
        ]
        
        for pattern, normalizer in relative_direction_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                span = (match.start(), match.end())
                if span in seen_spans:
                    continue
                evidence = match.group(0).strip()
                normalized = normalizer(match)
                time_expressions.append({
                    "time_id": f"T{time_id_counter}",
                    "evidence": evidence,
                    "normalized": normalized,
                    "granularity": TimeGranularity.RELATIVE,
                    "span": span
                })
                seen_spans.add(span)
                time_id_counter += 1
        
        # 4.2 单词型：yesterday, today, tomorrow
        relative_word_patterns = [
            (r'\b(yesterday)\b', 'YESTERDAY'),
            (r'\b(today)\b', 'TODAY'),
            (r'\b(tomorrow)\b', 'TOMORROW'),
        ]
        
        for pattern, normalized in relative_word_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                span = (match.start(), match.end())
                if span in seen_spans:
                    continue
                evidence = match.group(0).strip()
                time_expressions.append({
                    "time_id": f"T{time_id_counter}",
                    "evidence": evidence,
                    "normalized": normalized,
                    "granularity": TimeGranularity.RELATIVE,
                    "span": span
                })
                seen_spans.add(span)
                time_id_counter += 1
        
        # 4.3 星期几：Monday, Tuesday, ..., on Monday, last Friday, next Sunday
        # 按照从具体到宽泛的顺序匹配
        weekday_patterns = [
            # 1. 方向型：last/next + weekday
            (r'\b((?:last|next)\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday))\b', 
             lambda m: m.group(1).upper().replace(' ', '_')),
            # 2. 介词 + 星期 + 时段（最具体）
            (r'\b(?:on|for)\s+((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(?:morning|afternoon|evening|night))\b',
             lambda m: m.group(1).upper().replace(' ', '_')),
            # 3. 星期 + 时段（无介词）
            (r'\b((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(?:morning|afternoon|evening|night))\b',
             lambda m: m.group(1).upper().replace(' ', '_')),
            # 4. 介词 + 星期（最宽泛）
            (r'\b(?:on|for)\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b',
             lambda m: m.group(1).upper()),
        ]
        
        weekday_spans = []  # 用于检测覆盖
        
        def _is_covered_by_weekday(span, existing_spans):
            """检查 span 是否被已有的星期表达式覆盖"""
            for s, e in existing_spans:
                if s <= span[0] and span[1] <= e:
                    return True
            return False
        
        for pattern, normalizer in weekday_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                span = (match.start(), match.end())
                if span in seen_spans:
                    continue
                # 检查是否被已有的星期表达式覆盖
                if _is_covered_by_weekday(span, weekday_spans):
                    continue
                    
                evidence = match.group(0).strip()
                normalized = normalizer(match)
                time_expressions.append({
                    "time_id": f"T{time_id_counter}",
                    "evidence": evidence,
                    "normalized": normalized,
                    "granularity": TimeGranularity.RELATIVE,
                    "span": span
                })
                seen_spans.add(span)
                weekday_spans.append(span)
                time_id_counter += 1
        
        # 4.4 数字型：2 years ago, 3 months ago
        relative_numeric_pattern = r'\b(\d+)\s+(years?|months?|weeks?|days?)\s+ago\b'
        for match in re.finditer(relative_numeric_pattern, text, re.IGNORECASE):
            span = (match.start(), match.end())
            if span in seen_spans:
                continue
            evidence = match.group(0).strip()
            number = match.group(1)
            unit = match.group(2).upper()
            # 统一单复数
            if not unit.endswith('S'):
                unit += 'S'
            normalized = f"{number}_{unit}_AGO"
            time_expressions.append({
                "time_id": f"T{time_id_counter}",
                "evidence": evidence,
                "normalized": normalized,
                "granularity": TimeGranularity.RELATIVE,
                "span": span
            })
            seen_spans.add(span)
            time_id_counter += 1
        
        # 5. Duration（four-and-a-half year contract, five-year deal, in five years, for 2 months）
        # 按照从具体到宽泛的顺序定义规则
        duration_patterns = [
            # 0. 独立的时间跨度（in five years, in 2 months, for 2 months）
            r'\b(?:in|within|after|over|for)\s+(\d+)\s+(years?|months?|weeks?|days?)\b',
            r'\b(?:in|within|after|over|for)\s+(\w+)\s+(years?|months?|weeks?|days?)\b',
            
            # 1a. 复合词 + 独立的 year/month/week + contract/deal
            #     例如: "four-and-a-half year contract"
            r'\b(\w+(?:-\w+)+)\s+(years?|months?|weeks?)\s+(contract|deal)\b',
            
            # 1b. 单词-year/month/week 作为整体 + contract/deal  
            #     例如: "five-year deal", "two-month contract"
            r'\b((\w+)-(years?|months?|weeks?))\s+(deal|contract)\b',
            
            # 2. 数字形式
            r'\b(\d+)\s+(years?|months?|weeks?)\s+(contract|deal)\b',
            
            # 3. 最宽泛：单个单词
            r'\b(\w+)\s+(years?|months?|weeks?)\s+(contract|deal)\b',
        ]
        
        # 辅助函数：检查 span 是否被已有的 duration 覆盖
        def _is_covered_by_duration(span, duration_spans):
            """检查 span 是否被已有 duration 完全覆盖"""
            for s, e in duration_spans:
                if s <= span[0] and span[1] <= e:
                    return True
            return False
        
        duration_spans = []  # 记录已识别的 duration spans
        
        for pattern_idx, pattern in enumerate(duration_patterns):
            for match in re.finditer(pattern, text, re.IGNORECASE):
                span = (match.start(), match.end())
                
                # 检查是否已被识别（seen_spans）
                if span in seen_spans:
                    continue
                
                # 检查是否被已有的 duration 覆盖
                if _is_covered_by_duration(span, duration_spans):
                    continue
                
                evidence = match.group(0).strip()
                
                # 根据不同的模式提取 duration 和 unit
                if pattern_idx == 0:  # 模式 0: "in 5 years" (数字)
                    duration = match.group(1)  # 5
                    unit = match.group(2)      # years/year
                    normalized = f"{duration} {unit}"
                elif pattern_idx == 1:  # 模式 1: "in five years" (单词)
                    duration = match.group(1)  # five
                    unit = match.group(2)      # years/year
                    normalized = f"{duration} {unit}"
                elif pattern_idx == 2:  # 模式 2 (原1a): "four-and-a-half year contract"
                    duration = match.group(1)  # four-and-a-half
                    unit = match.group(2)      # years/year
                    normalized = f"{duration} {unit}"
                elif pattern_idx == 3:  # 模式 3 (原1b): "five-year deal"
                    duration = match.group(2)  # five (从 five-year 中提取)
                    unit = match.group(3)      # years/year
                    normalized = f"{duration} {unit}"
                elif pattern_idx == 4:  # 模式 4 (原2): "5 years contract"
                    duration = match.group(1)  # 5
                    unit = match.group(2)      # years/year
                    normalized = f"{duration} {unit}"
                elif pattern_idx == 5:  # 模式 5 (原3): "three year contract"
                    duration = match.group(1)  # three
                    unit = match.group(2)      # years/year
                    normalized = f"{duration} {unit}"
                else:
                    duration = match.group(1)
                    normalized = duration
                
                time_expressions.append({
                    "time_id": f"T{time_id_counter}",
                    "evidence": evidence,
                    "normalized": normalized,
                    "granularity": TimeGranularity.DURATION,
                    "span": span
                })
                seen_spans.add(span)
                duration_spans.append(span)  # 记录到 duration_spans
                time_id_counter += 1
        
        return time_expressions
    
    def _normalize_date(self, date_str: str) -> Optional[str]:
        """
        将日期字符串标准化为 YYYY-MM-DD 格式
        
        Args:
            date_str: 日期字符串（多种格式）
            
        Returns:
            标准化的日期字符串 (YYYY-MM-DD)，失败返回 None
        """
        date_str = date_str.strip()
        
        # 尝试多种日期格式
        formats = [
            "%d %B %Y",      # 1 September 2025
            "%B %d, %Y",     # September 1, 2025
            "%B %d %Y",      # September 1 2025
            "%B %Y %d",      # September 2025 01 (用于年月转换)
            "%Y-%m-%d",      # 2025-09-01
            "%d-%m-%Y",      # 01-09-2025
            "%m/%d/%Y",      # 09/01/2025
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        return None
