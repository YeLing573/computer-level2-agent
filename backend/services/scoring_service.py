from backend.models.schemas import ScoreResult


class AnswerScorer:
    """答案评分服务"""

    def score(self, answer: str, score_steps: list[dict]) -> ScoreResult:
        """
        根据评分步骤对答案进行评分。
        
        每个 score_step 格式:
            {"step": "步骤描述", "keywords": ["关键词1", "关键词2"], "score": 分值}
        
        规则：
        - 检查 answer 中是否包含 keywords 中的任一个关键词（不区分大小写）
        - 匹配到关键词即得对应分值
        """
        answer_lower = answer.lower()
        details = []
        total_score = 0.0
        max_score = 0.0

        for step in score_steps:
            step_name = step.get("step", "")
            keywords = step.get("keywords", [])
            step_score = float(step.get("score", 0))
            max_score += step_score

            matched = False
            for keyword in keywords:
                if keyword.lower() in answer_lower:
                    matched = True
                    break

            if matched:
                total_score += step_score

            details.append({
                "step": step_name,
                "score": step_score if matched else 0.0,
                "max_score": step_score,
                "matched": matched
            })

        percentage = round(total_score / max_score * 100, 2) if max_score > 0 else 0.0

        return ScoreResult(
            total_score=total_score,
            max_score=max_score,
            percentage=percentage,
            details=details
        )
