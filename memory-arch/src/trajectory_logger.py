"""
轨迹日志模块（Trajectory Logger）

Phase 0 - C进化数据采集V0基础设施
纯旁路记录，不影响现有系统运行

记录内容：
- 查询 query
- 检索到的记忆列表 retrieved_memories
- 实际被引用的记忆 referenced_memories
- 最终任务结果 outcome
- 上下文信息 context

用途：
- 为 Phase 3 状态匹配算法验证积累数据
- 为方案C（JitRL策略优化）提供离线训练数据
"""

import json
import uuid
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any

# 路径配置
BASE_DIR = Path(__file__).parent.parent
TRAJECTORY_LOG_PATH = BASE_DIR / "trajectory_log.jsonl"

# 时区：东八区
TZ = timezone(timedelta(hours=8))


def _now_iso() -> str:
    """获取当前时间的 ISO 格式字符串（东八区）"""
    return datetime.now(TZ).isoformat()


def _generate_trajectory_id() -> str:
    """生成唯一的轨迹ID（短UUID + 时间戳前缀）"""
    timestamp = datetime.now(TZ).strftime("%Y%m%d_%H%M%S")
    short_uuid = uuid.uuid4().hex[:8]
    return f"traj_{timestamp}_{short_uuid}"


def log_trajectory(
    query: str,
    retrieved_memories: List[Dict[str, Any]],
    referenced_memories: List[str] = None,
    outcome: str = "unknown",
    context: Dict[str, Any] = None
) -> str:
    """
    记录一条检索轨迹（append-only 写入 trajectory_log.jsonl）
    
    这是纯旁路记录，不会影响主检索流程的任何行为。
    写入失败时静默返回空字符串，避免影响主流程。
    
    Args:
        query: 用户查询文本
        retrieved_memories: 检索到的记忆列表（hybrid_retrieve 的返回值）
            每个元素至少包含 node_id, confidence, source_type
        referenced_memories: 实际被引用/使用的记忆ID列表（可选，任务完成后回填）
        outcome: 任务结果：
            - "success"：任务成功完成
            - "partial"：部分成功/降级完成
            - "failure"：任务失败
            - "unknown"：未知（默认，待回填）
        context: 额外的上下文信息字典（可选）
            如 task_type, session_id, timestamp 等
    
    Returns:
        trajectory_id: 生成的轨迹ID（可用于后续回填）
        写入失败时返回空字符串
    """
    try:
        trajectory_id = _generate_trajectory_id()
        
        # 提取检索结果的核心信息（精简存储）
        retrieved_simplified = []
        for mem in retrieved_memories:
            retrieved_simplified.append({
                "node_id": mem.get("node_id", ""),
                "confidence": mem.get("confidence", 0.0),
                "source_type": mem.get("source_type", ""),
                "content_preview": mem.get("content", "")[:100]  # 仅存前100字作参考
            })
        
        trajectory = {
            "trajectory_id": trajectory_id,
            "timestamp": _now_iso(),
            "query": query,
            "retrieved_memories": retrieved_simplified,
            "referenced_memories": referenced_memories or [],
            "outcome": outcome,
            "context": context or {}
        }
        
        # append-only 写入
        with open(TRAJECTORY_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(trajectory, ensure_ascii=False) + '\n')
        
        return trajectory_id
    
    except Exception as e:
        # 静默失败，不影响主流程
        print(f"[trajectory_logger] 写入失败: {e}")
        return ""


def update_trajectory_outcome(
    trajectory_id: str,
    referenced_memories: List[str] = None,
    outcome: str = None,
    additional_context: Dict[str, Any] = None
) -> bool:
    """
    回填轨迹的结果信息（任务完成后调用）
    
    注意：由于是 append-only 文件，回填会写入一条新的"更新记录"，
    而不是修改原记录。处理轨迹时按 trajectory_id 合并最新状态。
    
    Args:
        trajectory_id: 需要回填的轨迹ID
        referenced_memories: 实际引用的记忆ID列表
        outcome: 任务结果
        additional_context: 额外补充的上下文
    
    Returns:
        bool: 是否写入成功
    """
    try:
        update_record = {
            "trajectory_id": trajectory_id,
            "timestamp": _now_iso(),
            "type": "update",
            "referenced_memories": referenced_memories,
            "outcome": outcome,
            "additional_context": additional_context or {}
        }
        
        with open(TRAJECTORY_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(update_record, ensure_ascii=False) + '\n')
        
        return True
    
    except Exception as e:
        print(f"[trajectory_logger] 回填失败: {e}")
        return False


def count_trajectories() -> int:
    """
    统计当前轨迹日志中的轨迹数量（不含更新记录）
    
    Returns:
        int: 轨迹条目数
    """
    if not TRAJECTORY_LOG_PATH.exists():
        return 0
    
    count = 0
    try:
        with open(TRAJECTORY_LOG_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                try:
                    record = json.loads(line)
                    # 只统计初始轨迹记录，不含 update 类型
                    if record.get("type") != "update":
                        count += 1
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    
    return count


# ---------- 独立运行：自检 ----------
if __name__ == "__main__":
    print("=" * 50)
    print("Trajectory Logger 自检")
    print("=" * 50)
    
    # 测试写入
    print("\n[测试1] 写入一条测试轨迹...")
    test_retrieved = [
        {"node_id": "kn_001", "confidence": 0.85, "source_type": "knowledge_node",
         "content": "重大决策必须在24小时内写入decision log..."},
        {"node_id": "kn_002", "confidence": 0.72, "source_type": "knowledge_node",
         "content": "决策即记录机制采用三管齐下闭环..."},
    ]
    
    traj_id = log_trajectory(
        query="决策即记录机制是怎么落地的",
        retrieved_memories=test_retrieved,
        referenced_memories=["kn_001", "kn_002"],
        outcome="success",
        context={"task_type": "knowledge_query", "test": True}
    )
    
    print(f"  轨迹ID: {traj_id}")
    print(f"  写入状态: {'成功' if traj_id else '失败'}")
    
    # 测试回填
    if traj_id:
        print("\n[测试2] 回填测试轨迹...")
        result = update_trajectory_outcome(
            trajectory_id=traj_id,
            outcome="success",
            additional_context={"completed_at": "2026-08-26T00:00:00+08:00"}
        )
        print(f"  回填状态: {'成功' if result else '失败'}")
    
    # 统计
    print(f"\n[测试3] 当前轨迹总数: {count_trajectories()}")
    
    print("\n" + "=" * 50)
    print("自检完成！")
    print("=" * 50)
