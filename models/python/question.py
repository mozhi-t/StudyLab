from __future__ import annotations

import ast
from dataclasses import dataclass, field


@dataclass(frozen=True)
class OutputTestCase:
    id: str
    expected_stdout: str
    stdin: str = ""


@dataclass(frozen=True)
class CodeFeatureRule:
    id: str
    kind: str
    value: str = ""
    weight: float = 1.0


@dataclass(frozen=True)
class ExecutionPoint:
    id: str
    type: str
    score: float
    name: str = "程序正常运行"
    timeout_seconds: float = 3.0


@dataclass(frozen=True)
class OutputPoint:
    id: str
    type: str
    score: float
    cases: list[OutputTestCase] = field(default_factory=list)
    name: str = "输出测试"
    compare_mode: str = "normalized_text"

    def __post_init__(self) -> None:
        object.__setattr__(self, "cases", [item if isinstance(item, OutputTestCase) else OutputTestCase(**item) for item in self.cases])


@dataclass(frozen=True)
class CodeFeaturePoint:
    id: str
    type: str
    score: float
    rules: list[CodeFeatureRule] = field(default_factory=list)
    name: str = "关键代码检查"
    minimum_match_ratio: float = 0.8

    def __post_init__(self) -> None:
        object.__setattr__(self, "rules", [item if isinstance(item, CodeFeatureRule) else CodeFeatureRule(**item) for item in self.rules])


GradingPoint = ExecutionPoint | OutputPoint | CodeFeaturePoint


def _grading_point(payload: dict) -> GradingPoint:
    point_type = payload.get("type")
    classes = {
        "execution": ExecutionPoint,
        "output": OutputPoint,
        "code_features": CodeFeaturePoint,
    }
    if point_type not in classes:
        raise ValueError(f"未知 Python 判分点类型: {point_type}")
    return classes[point_type](**payload)


@dataclass
class PythonQuestion:
    id: int
    code: str
    answer: str
    grading_points: list[GradingPoint]
    full_score: float

    def __post_init__(self) -> None:
        self.grading_points = [item if isinstance(item, (ExecutionPoint, OutputPoint, CodeFeaturePoint)) else _grading_point(item) for item in self.grading_points]
        if self.full_score != 20:
            raise ValueError(f"Python 题目 {self.id} 的满分必须为 20 分")
        if self.code.count("#********Program********") != 1 or self.code.count("#********End********") != 1:
            raise ValueError(f"Python 题目 {self.id} 必须包含一对 Program/End 标志")
        if abs(sum(point.score for point in self.grading_points) - self.full_score) > 1e-9:
            raise ValueError(f"Python 题目 {self.id} 的判分点总分与满分不一致")
        point_ids = [point.id for point in self.grading_points]
        if len(point_ids) != len(set(point_ids)):
            raise ValueError(f"Python 题目 {self.id} 存在重复的判分点 ID")
        required_types = (ExecutionPoint, OutputPoint, CodeFeaturePoint)
        if any(not any(isinstance(point, required) for point in self.grading_points) for required in required_types):
            raise ValueError(f"Python 题目 {self.id} 必须包含运行、输出和关键代码判分点")
        feature_points = [point for point in self.grading_points if isinstance(point, CodeFeaturePoint)]
        if feature_points and any(len(point.rules) < 5 for point in feature_points):
            raise ValueError(f"Python 题目 {self.id} 的关键代码规则不得少于 5 条")
        try:
            description = ast.get_docstring(ast.parse(self.code), clean=False) or ""
        except SyntaxError as exc:
            raise ValueError(f"Python 题目 {self.id} 的代码模板语法无效: {exc}") from exc
        named_rule_kinds = {"function_definition", "name", "return_name"}
        required_names = {
            rule.value
            for point in feature_points
            for rule in point.rules
            if rule.kind in named_rule_kinds and rule.value
        }
        missing_names = sorted(name for name in required_names if name not in description)
        if missing_names:
            raise ValueError(
                f"Python 题目 {self.id} 的题目说明未展示判分所需名称: {', '.join(missing_names)}"
            )
        for point in self.grading_points:
            if isinstance(point, OutputPoint) and any(case.stdin for case in point.cases) and len(point.cases) < 2:
                raise ValueError(f"Python 题目 {self.id} 的输入测试数据不得少于 2 组")


@dataclass
class PythonQuestionBank:
    name: str
    subject: str
    create_time: str
    difficulty: int
    total_questions: int
    questions: list[PythonQuestion] = field(default_factory=list)
    question_type: str = "python_programming"

    def __post_init__(self) -> None:
        self.questions = [item if isinstance(item, PythonQuestion) else PythonQuestion(**item) for item in self.questions]
        if self.subject != "python" or self.question_type != "python_programming":
            raise ValueError("Python 编程题库的 subject/question_type 无效")
        if self.total_questions != len(self.questions):
            raise ValueError("Python 题库 total_questions 与实际题数不一致")
        question_ids = [question.id for question in self.questions]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Python 题库中存在重复的题目 ID")
